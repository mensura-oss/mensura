from collections.abc import Sequence
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.models import Run, RunStatus, Task, Workspace


class DuplicateWorkspaceRootError(Exception):
    """Raised when a repository cannot preserve unique workspace roots."""


class CoreRepository(Protocol):
    def list_workspaces(self) -> Sequence[Workspace]: ...

    def get_workspace(self, workspace_id: UUID) -> Workspace | None: ...

    def add_workspace(self, workspace: Workspace) -> None: ...

    def get_task(self, task_id: UUID) -> Task | None: ...

    def add_task(self, task: Task) -> None: ...

    def list_tasks_by_workspace(self, workspace_id: UUID) -> Sequence[Task]: ...

    def get_run(self, run_id: UUID) -> Run | None: ...

    def add_run(self, run: Run) -> None: ...

    def list_runs_by_workspace(self, workspace_id: UUID) -> Sequence[Run]: ...

    def replace_run_if_status(self, run: Run, expected_status: RunStatus) -> bool: ...


class InMemoryCoreRepository:
    """Process-local repository adapter; replaceable without changing HTTP routes."""

    def __init__(self) -> None:
        self._workspaces: dict[UUID, Workspace] = {}
        self._workspace_ids_by_root: dict[str, UUID] = {}
        self._tasks: dict[UUID, Task] = {}
        self._runs: dict[UUID, Run] = {}
        self._lock = RLock()

    def list_workspaces(self) -> Sequence[Workspace]:
        with self._lock:
            return tuple(
                sorted(self._workspaces.values(), key=lambda workspace: workspace.created_at)
            )

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        with self._lock:
            return self._workspaces.get(workspace_id)

    def add_workspace(self, workspace: Workspace) -> None:
        with self._lock:
            if workspace.root_path in self._workspace_ids_by_root:
                raise DuplicateWorkspaceRootError(workspace.root_path)
            self._workspaces[workspace.id] = workspace
            self._workspace_ids_by_root[workspace.root_path] = workspace.id

    def get_task(self, task_id: UUID) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def add_task(self, task: Task) -> None:
        with self._lock:
            self._tasks[task.id] = task

    def list_tasks_by_workspace(self, workspace_id: UUID) -> Sequence[Task]:
        with self._lock:
            return tuple(
                sorted(
                    (task for task in self._tasks.values() if task.workspace_id == workspace_id),
                    key=lambda task: task.created_at,
                )
            )

    def get_run(self, run_id: UUID) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def add_run(self, run: Run) -> None:
        with self._lock:
            self._runs[run.id] = run

    def list_runs_by_workspace(self, workspace_id: UUID) -> Sequence[Run]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        run
                        for run in self._runs.values()
                        if run.context_pack.workspace_id == workspace_id
                    ),
                    key=lambda run: run.created_at,
                )
            )

    def replace_run_if_status(self, run: Run, expected_status: RunStatus) -> bool:
        with self._lock:
            current = self._runs.get(run.id)
            if current is None or current.status is not expected_status:
                return False
            self._runs[run.id] = run
            return True
