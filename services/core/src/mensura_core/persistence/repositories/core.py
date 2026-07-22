from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.models import Run, RunStatus, Task, Workspace
from mensura_core.persistence.models import RunRow, TaskRow, WorkspaceRow
from mensura_core.repositories import DuplicateWorkspaceRootError


class SqlCoreRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def list_workspaces(self) -> Sequence[Workspace]:
        with self._sf() as session:
            rows = session.query(WorkspaceRow).order_by(WorkspaceRow.created_at).all()
            return tuple(row.to_domain() for row in rows)

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        with self._sf() as session:
            row = session.get(WorkspaceRow, workspace_id)
            return row.to_domain() if row is not None else None

    def add_workspace(self, workspace: Workspace) -> None:
        with self._sf() as session:
            existing = (
                session.query(WorkspaceRow)
                .filter(WorkspaceRow.root_path == workspace.root_path)
                .first()
            )
            if existing is not None:
                raise DuplicateWorkspaceRootError(workspace.root_path)
            session.add(WorkspaceRow.from_domain(workspace))
            session.commit()

    def get_task(self, task_id: UUID) -> Task | None:
        with self._sf() as session:
            row = session.get(TaskRow, task_id)
            return row.to_domain() if row is not None else None

    def add_task(self, task: Task) -> None:
        with self._sf() as session:
            session.add(TaskRow.from_domain(task))
            session.commit()

    def list_tasks_by_workspace(self, workspace_id: UUID) -> Sequence[Task]:
        with self._sf() as session:
            rows = (
                session.query(TaskRow)
                .filter(TaskRow.workspace_id == workspace_id)
                .order_by(TaskRow.created_at)
                .all()
            )
            return tuple(row.to_domain() for row in rows)

    def get_run(self, run_id: UUID) -> Run | None:
        with self._sf() as session:
            row = session.get(RunRow, run_id)
            return row.to_domain() if row is not None else None

    def add_run(self, run: Run) -> None:
        with self._sf() as session:
            session.add(RunRow.from_domain(run))
            session.commit()

    def list_runs_by_workspace(self, workspace_id: UUID) -> Sequence[Run]:
        with self._sf() as session:
            rows = (
                session.query(RunRow)
                .filter(RunRow.workspace_id == workspace_id)
                .order_by(RunRow.created_at)
                .all()
            )
            return tuple(row.to_domain() for row in rows)

    def replace_run_if_status(self, run: Run, expected_status: RunStatus) -> bool:
        with self._sf() as session:
            row = session.get(RunRow, run.id)
            if row is None or RunStatus(row.status) is not expected_status:
                return False
            row.task_id = run.task_id
            row.workspace_id = run.context_pack.workspace_id
            row.context_pack_id = run.context_pack_id
            row._context_pack = run.context_pack.model_dump(by_alias=False, mode="json")
            row.status = run.status.value
            row._execution = (
                run.execution.model_dump(by_alias=False, mode="json")
                if run.execution is not None
                else None
            )
            row.started_at = run.started_at
            row.finished_at = run.finished_at
            row.updated_at = run.updated_at
            session.commit()
            return True
