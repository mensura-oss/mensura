import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from time import perf_counter
from uuid import UUID, uuid4

from mensura_core.exceptions import (
    GuardExecutionError,
    GuardRunInProgressError,
    GuardRunNotFoundError,
    ResourceNotFoundError,
)
from mensura_core.guard_config import GuardConfigurationLoader
from mensura_core.guard_models import (
    GuardCheckKind,
    GuardCheckResult,
    GuardCheckStatus,
    GuardCommandConfiguration,
    GuardRunCreate,
    GuardRunResponse,
    GuardRunStatus,
    GuardSummary,
)
from mensura_core.guard_repositories import GuardRunRepository
from mensura_core.guard_runner import CommandExecution, CommandStartError, GuardCommandRunner
from mensura_core.models import Workspace, ensure_utc_timestamp
from mensura_core.repositories import CoreRepository

IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]
Monotonic = Callable[[], float]


def utc_now() -> datetime:
    return datetime.now(UTC)


class GuardService:
    """Synchronous, manually triggered Guard application service."""

    def __init__(
        self,
        core_repository: CoreRepository,
        configuration_loader: GuardConfigurationLoader,
        command_runner: GuardCommandRunner,
        run_repository: GuardRunRepository,
        *,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
        monotonic: Monotonic = perf_counter,
    ) -> None:
        self._core_repository = core_repository
        self._configuration_loader = configuration_loader
        self._command_runner = command_runner
        self._run_repository = run_repository
        self._id_factory = id_factory
        self._clock = clock
        self._monotonic = monotonic
        self._active_workspaces: set[UUID] = set()
        self._active_lock = Lock()

    def create_run(self, workspace_id: UUID, payload: GuardRunCreate) -> GuardRunResponse:
        workspace = self._require_workspace(workspace_id)
        self._reserve(workspace_id)
        try:
            return self._execute(workspace, payload)
        finally:
            self._release(workspace_id)

    def get_latest(self, workspace_id: UUID) -> GuardRunResponse:
        self._require_workspace(workspace_id)
        run = self._run_repository.get_latest(workspace_id)
        if run is None:
            raise GuardRunNotFoundError(workspace_id)
        return run

    def _execute(self, workspace: Workspace, payload: GuardRunCreate) -> GuardRunResponse:
        configuration = self._configuration_loader.load(workspace.root_path)
        requested_checks = payload.checks or [GuardCheckKind.LINT, GuardCheckKind.TEST]
        started_at = ensure_utc_timestamp(self._clock())
        started = self._monotonic()
        results: list[GuardCheckResult] = []

        for kind in requested_checks:
            check_config = getattr(configuration.checks, kind.value)
            try:
                execution = self._command_runner.run(
                    check_config.command,
                    cwd=Path(workspace.root_path),
                    timeout_seconds=configuration.timeout_seconds,
                )
            except CommandStartError as error:
                raise GuardExecutionError(kind.value) from error
            results.append(
                self._normalize(kind, check_config, execution, configuration.timeout_seconds)
            )

        completed_at = ensure_utc_timestamp(self._clock())
        blocking_failures = sum(
            result.blocking and result.status is not GuardCheckStatus.PASSED for result in results
        )
        passed_count = sum(result.status is GuardCheckStatus.PASSED for result in results)
        failed_count = sum(result.status is GuardCheckStatus.FAILED for result in results)
        error_count = sum(result.status is GuardCheckStatus.ERROR for result in results)
        summary = GuardSummary(
            total_count=len(results),
            passed_count=passed_count,
            failed_count=failed_count,
            error_count=error_count,
            blocking_failures=blocking_failures,
            is_blocking=blocking_failures > 0,
        )
        run = GuardRunResponse(
            id=self._id_factory(),
            workspace_id=workspace.id,
            status=(
                GuardRunStatus.PASSED if passed_count == len(results) else GuardRunStatus.FAILED
            ),
            blocking=summary.is_blocking,
            summary=summary,
            checks=results,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=max(0, round((self._monotonic() - started) * 1000)),
        )
        self._run_repository.save_latest(run)
        return run

    def _normalize(
        self,
        kind: GuardCheckKind,
        configuration: GuardCommandConfiguration,
        execution: CommandExecution,
        timeout_seconds: int,
    ) -> GuardCheckResult:
        if execution.timed_out:
            status = GuardCheckStatus.ERROR
            summary = f"{self._label(kind)} timed out after {timeout_seconds} seconds."
        elif execution.exit_code == 0:
            status = GuardCheckStatus.PASSED
            summary = f"{self._label(kind)} passed."
        else:
            status = GuardCheckStatus.FAILED
            summary = self._failure_summary(kind, execution)

        return GuardCheckResult(
            kind=kind,
            status=status,
            blocking=configuration.blocking,
            summary=summary,
            command=configuration.command,
            exit_code=execution.exit_code,
            duration_ms=execution.duration_ms,
            stdout=execution.stdout,
            stderr=execution.stderr,
            output_truncated=execution.output_truncated,
        )

    def _failure_summary(self, kind: GuardCheckKind, execution: CommandExecution) -> str:
        if kind is GuardCheckKind.LINT:
            try:
                diagnostics = json.loads(execution.stdout)
            except json.JSONDecodeError:
                diagnostics = None
            if isinstance(diagnostics, list):
                count = len(diagnostics)
                noun = "diagnostic" if count == 1 else "diagnostics"
                return f"Lint failed with {count} {noun}."
        return f"{self._label(kind)} failed with exit code {execution.exit_code}."

    def _label(self, kind: GuardCheckKind) -> str:
        return "Lint" if kind is GuardCheckKind.LINT else "Tests"

    def _require_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self._core_repository.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace", workspace_id)
        return workspace

    def _reserve(self, workspace_id: UUID) -> None:
        with self._active_lock:
            if workspace_id in self._active_workspaces:
                raise GuardRunInProgressError(workspace_id)
            self._active_workspaces.add(workspace_id)

    def _release(self, workspace_id: UUID) -> None:
        with self._active_lock:
            self._active_workspaces.discard(workspace_id)
