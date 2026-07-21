from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.application_models import ApplicationArtifact
from mensura_core.persistence.models import ApplicationRow


class SqlApplicationRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def save_if_absent_for_proposal(self, application: ApplicationArtifact) -> bool:
        with self._sf() as session:
            existing = (
                session.query(ApplicationRow)
                .filter(ApplicationRow.proposal_id == application.proposal_id)
                .first()
            )
            if existing is not None:
                return False
            session.add(ApplicationRow.from_domain(application))
            session.commit()
            return True

    def get(self, application_id: UUID) -> ApplicationArtifact | None:
        with self._sf() as session:
            row = session.get(ApplicationRow, application_id)
            return row.to_domain() if row is not None else None

    def get_for_proposal(self, proposal_id: UUID) -> ApplicationArtifact | None:
        with self._sf() as session:
            row = (
                session.query(ApplicationRow)
                .filter(ApplicationRow.proposal_id == proposal_id)
                .first()
            )
            return row.to_domain() if row is not None else None

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[ApplicationArtifact]:
        with self._sf() as session:
            rows = (
                session.query(ApplicationRow)
                .filter(ApplicationRow.workspace_id == workspace_id)
                .order_by(ApplicationRow.created_at, ApplicationRow.id)
                .all()
            )
            return tuple(row.to_domain() for row in rows)
