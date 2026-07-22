from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.backup_models import BackupArtifact
from mensura_core.persistence.models import BackupRow


class SqlBackupRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def add(self, backup: BackupArtifact) -> None:
        with self._sf() as session:
            session.add(BackupRow.from_domain(backup))
            session.commit()

    def get(self, backup_id: UUID) -> BackupArtifact | None:
        with self._sf() as session:
            row = session.get(BackupRow, backup_id)
            return row.to_domain() if row is not None else None

    def delete(self, backup_id: UUID) -> bool:
        with self._sf() as session:
            row = session.get(BackupRow, backup_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def list_all(self) -> Sequence[BackupArtifact]:
        with self._sf() as session:
            rows = (
                session.query(BackupRow)
                .order_by(BackupRow.created_at.desc(), BackupRow.id.desc())
                .all()
            )
            return tuple(row.to_domain() for row in rows)
