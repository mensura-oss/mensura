from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mensura_core.exceptions import ResourceConflictError, ResourceNotFoundError
from mensura_core.git_adapter import GitRepositoryAdapter
from mensura_core.models import (
    Run,
    RunStatus,
    Task,
    TaskCreate,
    TaskStatus,
    Workspace,
    WorkspaceCreate,
    ensure_utc_timestamp,
)
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
        *,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
    ) -> None:
        self._repository = repository
        self._git_repository = git_repository
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

    def create_run(self, task_id: UUID) -> Run:
        self.get_task(task_id)
        timestamp = ensure_utc_timestamp(self._clock())
        run = Run(
            id=self._id_factory(),
            task_id=task_id,
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

    def _require_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self._repository.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace", workspace_id)
        return workspace
