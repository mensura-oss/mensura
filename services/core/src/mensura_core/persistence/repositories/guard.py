from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.guard_models import GuardRunResponse
from mensura_core.persistence.models import GuardRunRow


class SqlGuardRunRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def get_latest(self, workspace_id: UUID) -> GuardRunResponse | None:
        with self._sf() as session:
            row = (
                session.query(GuardRunRow).filter(GuardRunRow.workspace_id == workspace_id).first()
            )
            return row.to_domain() if row is not None else None

    def save_latest(self, run: GuardRunResponse) -> None:
        with self._sf() as session:
            existing = session.get(GuardRunRow, run.id)
            if existing is not None:
                existing.status = run.status.value
                existing.blocking = run.blocking
                existing._summary = run.summary.model_dump(by_alias=False, mode="json")
                existing._checks = [
                    check.model_dump(by_alias=False, mode="json") for check in run.checks
                ]
                existing.started_at = run.started_at
                existing.completed_at = run.completed_at
                existing.duration_ms = run.duration_ms
            else:
                session.add(GuardRunRow.from_domain(run))
            session.commit()
