from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.persistence.models import (
    VaultChunkPostingRow,
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
    iter_chunk_postings,
)


def _to_chunk_vector(row: VaultChunkRow) -> ChunkVector:
    return ChunkVector(
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
            # Replace the sparse inverted index for this workspace atomically with the snapshot.
            # Postings carry no FK, so this explicit delete (not a cascade) removes the prior
            # acceleration structure before the new one is inserted in the same transaction.
            session.query(VaultChunkPostingRow).filter(
                VaultChunkPostingRow.workspace_id == record.snapshot.workspace_id
            ).delete(synchronize_session=False)
            snapshot, item_rows, chunk_rows = VaultIndexSnapshotRow.from_record(record)
            session.add(snapshot)
            session.add_all(item_rows)
            session.add_all(chunk_rows)
            # Empty for dense/legacy indexes (not acceleration-eligible) → those read as
            # "not accelerated" at query time and use the exact linear scan.
            session.add_all(
                VaultChunkPostingRow(
                    workspace_id=record.snapshot.workspace_id, chunk_id=chunk_id, bucket=bucket
                )
                for chunk_id, bucket in iter_chunk_postings(record)
            )
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
            return [_to_chunk_vector(row) for row in query.all()]

    def list_candidate_vectors(
        self,
        workspace_id: UUID,
        query_buckets: Sequence[str],
        *,
        source_type: VaultSourceType | None = None,
        candidate_limit: int,
    ) -> list[ChunkVector] | None:
        buckets = list(query_buckets)
        if not buckets:
            return None  # no buckets to probe → let the caller run the exact linear scan
        with self._sf() as session:
            # No postings for this workspace ⇒ dense/legacy/never-built ⇒ not accelerated.
            has_postings = (
                session.query(VaultChunkPostingRow.id)
                .filter(VaultChunkPostingRow.workspace_id == workspace_id)
                .first()
            )
            if has_postings is None:
                return None
            # Read only the posting lists for the query's buckets; stop one past the cap so a
            # query too broad to benefit falls back to the linear scan in a bounded way.
            chunk_id_rows = (
                session.query(VaultChunkPostingRow.chunk_id)
                .filter(
                    VaultChunkPostingRow.workspace_id == workspace_id,
                    VaultChunkPostingRow.bucket.in_(buckets),
                )
                .distinct()
                .limit(candidate_limit + 1)
                .all()
            )
            if len(chunk_id_rows) > candidate_limit:
                return None
            candidate_ids = [row.chunk_id for row in chunk_id_rows]
            if not candidate_ids:
                return []  # accelerated, but no chunk shares a query bucket → correct empty
            query = session.query(VaultChunkRow).filter(
                VaultChunkRow.workspace_id == workspace_id,
                VaultChunkRow.id.in_(candidate_ids),
            )
            if source_type is not None:
                query = query.filter(VaultChunkRow.source_type == source_type.value)
            return [_to_chunk_vector(row) for row in query.all()]
