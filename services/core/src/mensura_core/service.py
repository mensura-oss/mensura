from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ValidationError

from mensura_core.context_pack_models import ContextPackManifest
from mensura_core.context_pack_repositories import ContextPackRepository
from mensura_core.exceptions import (
    ContextPackNotFoundError,
    ContextPackWorkspaceMismatchError,
    ProviderExecutionFailedError,
    ResourceConflictError,
    ResourceNotFoundError,
    RunContextInconsistentError,
    RunContextPackMissingError,
    RunInvalidStateError,
    StructuredResultInvalidError,
)
from mensura_core.git_adapter import GitRepositoryAdapter
from mensura_core.models import (
    Run,
    RunContextPackReference,
    RunCreate,
    RunExecution,
    RunExecutionFailure,
    RunExecutionFailureCode,
    RunExecutionResult,
    RunProviderMetadata,
    RunStatus,
    Task,
    TaskCreate,
    TaskStatus,
    Workspace,
    WorkspaceCreate,
    ensure_utc_timestamp,
)
from mensura_core.provider_adapter import ProviderAdapter, ProviderExecutionRequest
from mensura_core.repositories import CoreRepository, DuplicateWorkspaceRootError
from mensura_core.repository_models import RepositorySummary

IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


class CoreService:
    """Application operations independent of FastAPI and storage implementation."""

    def __init__(
        self,
        repository: CoreRepository,
        git_repository: GitRepositoryAdapter,
        context_pack_repository: ContextPackRepository,
        provider: ProviderAdapter,
        *,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
    ) -> None:
        self._repository = repository
        self._git_repository = git_repository
        self._context_pack_repository = context_pack_repository
        self._provider = provider
        self._id_factory = id_factory
        self._clock = clock

    def list_workspaces(self) -> Sequence[Workspace]:
        return self._repository.list_workspaces()

    def create_workspace(self, payload: WorkspaceCreate) -> Workspace:
        timestamp = ensure_utc_timestamp(self._clock())
        workspace = Workspace(
            id=self._id_factory(),
            name=payload.name,
            root_path=payload.root_path,
            created_at=timestamp,
            updated_at=timestamp,
        )
        try:
            self._repository.add_workspace(workspace)
        except DuplicateWorkspaceRootError as error:
            raise ResourceConflictError(
                f"A workspace for root path '{error.args[0]}' already exists."
            ) from error
        return workspace

    def inspect_workspace_repository(self, workspace_id: UUID) -> RepositorySummary:
        workspace = self._require_workspace(workspace_id)
        inspection = self._git_repository.inspect(workspace.root_path)
        return RepositorySummary(workspace_id=workspace.id, **inspection.model_dump())

    def create_task(self, payload: TaskCreate) -> Task:
        self._require_workspace(payload.workspace_id)
        timestamp = ensure_utc_timestamp(self._clock())
        task = Task(
            id=self._id_factory(),
            workspace_id=payload.workspace_id,
            title=payload.title,
            description=payload.description,
            status=TaskStatus.READY,
            assigned_role=payload.assigned_role,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._repository.add_task(task)
        return task

    def get_task(self, task_id: UUID) -> Task:
        task = self._repository.get_task(task_id)
        if task is None:
            raise ResourceNotFoundError("Task", task_id)
        return task

    def create_run(self, task_id: UUID, payload: RunCreate) -> Run:
        task = self.get_task(task_id)
        context_pack = self._context_pack_repository.get(task.workspace_id, payload.context_pack_id)
        if context_pack is None:
            context_pack_in_other_workspace = self._context_pack_repository.find_by_id(
                payload.context_pack_id
            )
            if context_pack_in_other_workspace is not None:
                raise ContextPackWorkspaceMismatchError(
                    task.id,
                    task.workspace_id,
                    payload.context_pack_id,
                    context_pack_in_other_workspace.workspace_id,
                )
            raise ContextPackNotFoundError(payload.context_pack_id)

        timestamp = ensure_utc_timestamp(self._clock())
        summary = context_pack.summary
        run = Run(
            id=self._id_factory(),
            task_id=task_id,
            context_pack_id=context_pack.id,
            context_pack=RunContextPackReference(
                id=context_pack.id,
                workspace_id=context_pack.workspace_id,
                inventory_id=context_pack.inventory_id,
                schema_version=context_pack.schema_version,
                file_count=summary.file_count,
                total_file_bytes=summary.total_file_bytes,
                total_preview_bytes=summary.total_preview_bytes,
            ),
            status=RunStatus.QUEUED,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._repository.add_run(run)
        return run

    def get_run(self, run_id: UUID) -> Run:
        run = self._repository.get_run(run_id)
        if run is None:
            raise ResourceNotFoundError("Run", run_id)
        return run

    def execute_run(self, run_id: UUID) -> Run:
        run = self.get_run(run_id)
        if run.status is not RunStatus.QUEUED:
            raise RunInvalidStateError(run.id, run.status)

        task = self.get_task(run.task_id)
        self._validate_stored_binding(run, task)
        context_pack = self._context_pack_repository.get(task.workspace_id, run.context_pack_id)
        if context_pack is None:
            raise RunContextPackMissingError(run.id, run.context_pack_id)
        if not self._binding_matches_manifest(run, context_pack):
            raise RunContextInconsistentError(run.id)

        started_at = ensure_utc_timestamp(self._clock())
        running = Run.model_validate(
            {
                **run.model_dump(by_alias=False),
                "status": RunStatus.RUNNING,
                "execution": RunExecution(provider=self._provider.identity),
                "started_at": started_at,
                "updated_at": started_at,
            }
        )
        if not self._repository.replace_run_if_status(running, RunStatus.QUEUED):
            current = self.get_run(run.id)
            raise RunInvalidStateError(current.id, current.status)

        request = ProviderExecutionRequest(task=task, context_pack=context_pack)
        try:
            raw_result = self._provider.execute(request)
        except Exception as error:
            self._finish_failed_run(
                running,
                RunExecutionFailureCode.PROVIDER_EXECUTION_FAILED,
                "The provider adapter could not complete this execution.",
            )
            raise ProviderExecutionFailedError(run.id) from error

        try:
            result = RunExecutionResult.model_validate(raw_result)
        except (ValidationError, TypeError, ValueError) as error:
            self._finish_failed_run(
                running,
                RunExecutionFailureCode.STRUCTURED_RESULT_INVALID,
                "The provider returned output that did not satisfy the execution schema.",
            )
            raise StructuredResultInvalidError(run.id) from error

        finished_at, duration_ms = self._finished_timing(started_at)
        succeeded = Run.model_validate(
            {
                **running.model_dump(by_alias=False),
                "status": RunStatus.SUCCEEDED,
                "execution": RunExecution(
                    provider=self._running_provider(running),
                    duration_ms=duration_ms,
                    result=result,
                ),
                "finished_at": finished_at,
                "updated_at": finished_at,
            }
        )
        if not self._repository.replace_run_if_status(succeeded, RunStatus.RUNNING):
            raise RuntimeError(f"Run '{run.id}' left running state during provider execution.")
        return succeeded

    @staticmethod
    def _validate_stored_binding(run: Run, task: Task) -> None:
        if (
            run.task_id != task.id
            or run.context_pack_id != run.context_pack.id
            or task.workspace_id != run.context_pack.workspace_id
        ):
            raise RunContextInconsistentError(run.id)

    @staticmethod
    def _binding_matches_manifest(run: Run, context_pack: ContextPackManifest) -> bool:
        summary = context_pack.summary
        reference = run.context_pack
        return (
            context_pack.id == run.context_pack_id
            and context_pack.workspace_id == reference.workspace_id
            and context_pack.inventory_id == reference.inventory_id
            and context_pack.schema_version == reference.schema_version
            and summary.file_count == reference.file_count
            and summary.total_file_bytes == reference.total_file_bytes
            and summary.total_preview_bytes == reference.total_preview_bytes
        )

    def _finish_failed_run(
        self,
        running: Run,
        code: RunExecutionFailureCode,
        summary: str,
    ) -> None:
        if running.started_at is None:
            raise RuntimeError("A running run must have startedAt.")
        finished_at, duration_ms = self._finished_timing(running.started_at)
        failed = Run.model_validate(
            {
                **running.model_dump(by_alias=False),
                "status": RunStatus.FAILED,
                "execution": RunExecution(
                    provider=self._running_provider(running),
                    duration_ms=duration_ms,
                    failure=RunExecutionFailure(code=code, summary=summary),
                ),
                "finished_at": finished_at,
                "updated_at": finished_at,
            }
        )
        if not self._repository.replace_run_if_status(failed, RunStatus.RUNNING):
            raise RuntimeError(f"Run '{running.id}' left running state during provider execution.")

    @staticmethod
    def _running_provider(running: Run) -> RunProviderMetadata:
        if running.execution is None:
            raise RuntimeError("A running run must have provider identity.")
        return running.execution.provider

    def _finished_timing(self, started_at: datetime) -> tuple[datetime, int]:
        observed = ensure_utc_timestamp(self._clock())
        finished_at = max(started_at, observed)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        return finished_at, min(duration_ms, 86_400_000)

    def _require_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self._repository.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace", workspace_id)
        return workspace
