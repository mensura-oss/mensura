from collections.abc import Callable
from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from uuid import UUID, uuid4

from mensura_core.exceptions import (
    GuardRunInProgressError,
    GuardRunNotFoundError,
    ResourceNotFoundError,
)
from mensura_core.guard_config import GuardConfigurationLoader
from mensura_core.guard_execution import execute_guard_checks
from mensura_core.guard_models import (
    GuardCheckKind,
    GuardRunCreate,
    GuardRunResponse,
)
from mensura_core.guard_repositories import GuardRunRepository
from mensura_core.guard_runner import GuardCommandRunner
from mensura_core.models import Workspace
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
        requested_checks = payload.checks or [GuardCheckKind.LINT, GuardCheckKind.TEST]
        execution = execute_guard_checks(
            workspace.root_path,
            requested_checks,
            configuration_loader=self._configuration_loader,
            command_runner=self._command_runner,
            clock=self._clock,
            monotonic=self._monotonic,
        )
        run = GuardRunResponse(
            id=self._id_factory(),
            workspace_id=workspace.id,
            status=execution.status,
            blocking=execution.summary.is_blocking,
            summary=execution.summary,
            checks=execution.checks,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            duration_ms=execution.duration_ms,
        )
        self._run_repository.save_latest(run)
        return run

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
