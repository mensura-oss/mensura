from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.persistence.models import UndoRow
from mensura_core.undo_models import UndoArtifact


class SqlUndoRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def save_if_absent_for_application(self, undo: UndoArtifact) -> bool:
        with self._sf() as session:
            existing = (
                session.query(UndoRow)
                .filter(UndoRow.application_id == undo.application_id)
                .first()
            )
            if existing is not None:
                return False
            session.add(UndoRow.from_domain(undo))
            session.commit()
            return True

    def get(self, undo_id: UUID) -> UndoArtifact | None:
        with self._sf() as session:
            row = session.get(UndoRow, undo_id)
            return row.to_domain() if row is not None else None

    def get_for_application(self, application_id: UUID) -> UndoArtifact | None:
        with self._sf() as session:
            row = (
                session.query(UndoRow)
                .filter(UndoRow.application_id == application_id)
                .first()
            )
            return row.to_domain() if row is not None else None

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[UndoArtifact]:
        with self._sf() as session:
            rows = (
                session.query(UndoRow)
                .filter(UndoRow.workspace_id == workspace_id)
                .order_by(UndoRow.created_at, UndoRow.id)
                .all()
            )
            return tuple(row.to_domain() for row in rows)
