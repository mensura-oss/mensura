from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.context_pack_models import ContextPackManifest
from mensura_core.persistence.models import ContextPackRow


class SqlContextPackRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def save_if_absent(self, manifest: ContextPackManifest) -> bool:
        with self._sf() as session:
            existing = session.get(ContextPackRow, manifest.id)
            if existing is not None:
                return False
            session.add(ContextPackRow.from_domain(manifest))
            session.commit()
            return True

    def get(self, workspace_id: UUID, context_pack_id: str) -> ContextPackManifest | None:
        with self._sf() as session:
            row = (
                session.query(ContextPackRow)
                .filter(
                    ContextPackRow.workspace_id == workspace_id,
                    ContextPackRow.id == context_pack_id,
                )
                .first()
            )
            return row.to_domain() if row is not None else None

    def find_by_id(self, context_pack_id: str) -> ContextPackManifest | None:
        with self._sf() as session:
            row = session.get(ContextPackRow, context_pack_id)
            return row.to_domain() if row is not None else None

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[ContextPackManifest]:
        with self._sf() as session:
            rows = (
                session.query(ContextPackRow)
                .filter(ContextPackRow.workspace_id == workspace_id)
                .order_by(ContextPackRow.id)
                .all()
            )
            return tuple(row.to_domain() for row in rows)
