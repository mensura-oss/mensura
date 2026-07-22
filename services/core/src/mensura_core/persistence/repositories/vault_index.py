from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.persistence.models import (
    VaultChunkRow,
    VaultIndexSnapshotRow,
    VaultMemoryItemRow,
)
from mensura_core.vault_index_models import VaultIndexSnapshot, VaultSourceType
from mensura_core.vault_index_repositories import (
    ChunkVector,
    IndexedMemoryItem,
    VaultIndexRecord,
    VaultItemSummary,
)


class SqlVaultIndexRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def save_latest(self, record: VaultIndexRecord) -> None:
        with self._sf() as session:
            existing = (
                session.query(VaultIndexSnapshotRow)
                .filter(VaultIndexSnapshotRow.workspace_id == record.snapshot.workspace_id)
                .first()
            )
            if existing is not None:
                session.delete(existing)
                session.flush()
            snapshot, item_rows, chunk_rows = VaultIndexSnapshotRow.from_record(record)
            session.add(snapshot)
            session.add_all(item_rows)
            session.add_all(chunk_rows)
            session.commit()

    def get_snapshot(self, workspace_id: UUID) -> VaultIndexSnapshot | None:
        with self._sf() as session:
            row = (
                session.query(VaultIndexSnapshotRow)
                .filter(VaultIndexSnapshotRow.workspace_id == workspace_id)
                .first()
            )
            return row.to_snapshot() if row is not None else None

    def list_item_summaries(self, workspace_id: UUID) -> tuple[VaultItemSummary, ...]:
        with self._sf() as session:
            rows = (
                session.query(
                    VaultMemoryItemRow.path,
                    VaultMemoryItemRow.source_type,
                    VaultMemoryItemRow.language,
                    VaultMemoryItemRow.size_bytes,
                )
                .filter(VaultMemoryItemRow.workspace_id == workspace_id)
                .all()
            )
            return tuple(
                VaultItemSummary(
                    path=row.path,
                    source_type=VaultSourceType(row.source_type),
                    language=row.language,
                    size_bytes=row.size_bytes,
                )
                for row in rows
            )

    def get_memory_item(self, memory_item_id: UUID) -> IndexedMemoryItem | None:
        with self._sf() as session:
            row = session.get(VaultMemoryItemRow, memory_item_id)
            return row.to_domain() if row is not None else None

    def list_chunk_vectors(
        self, workspace_id: UUID, *, source_type: VaultSourceType | None = None
    ) -> list[ChunkVector]:
        with self._sf() as session:
            query = session.query(VaultChunkRow).filter(VaultChunkRow.workspace_id == workspace_id)
            if source_type is not None:
                query = query.filter(VaultChunkRow.source_type == source_type.value)
            return [
                ChunkVector(
                    chunk_id=row.id,
                    memory_item_id=row.memory_item_id,
                    path=row.path,
                    source_type=VaultSourceType(row.source_type),
                    language=row.language,
                    chunk_index=row.chunk_index,
                    start_line=row.start_line,
                    end_line=row.end_line,
                    text=row.text,
                    embedding=row._embedding,
                )
                for row in query.all()
            ]
