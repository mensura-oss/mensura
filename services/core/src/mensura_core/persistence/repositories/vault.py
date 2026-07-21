from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.persistence.models import VaultInventorySnapshotRow
from mensura_core.vault_repositories import VaultInventoryRecord


class SqlVaultInventoryRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def get_latest(self, workspace_id: UUID) -> VaultInventoryRecord | None:
        with self._sf() as session:
            row = (
                session.query(VaultInventorySnapshotRow)
                .filter(VaultInventorySnapshotRow.workspace_id == workspace_id)
                .first()
            )
            if row is None:
                return None
            items = tuple(item.to_domain() for item in row.items)
            return VaultInventoryRecord(snapshot=row.to_snapshot(), items=items)

    def save_latest(self, record: VaultInventoryRecord) -> None:
        with self._sf() as session:
            existing = (
                session.query(VaultInventorySnapshotRow)
                .filter(VaultInventorySnapshotRow.workspace_id == record.snapshot.workspace_id)
                .first()
            )
            if existing is not None:
                session.delete(existing)
                session.flush()
            snapshot, items = VaultInventorySnapshotRow.from_record(record)
            session.add(snapshot)
            session.add_all(items)
            session.commit()
