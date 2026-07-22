"""Internal index records and the Vault index repository boundary.

The dataclasses here carry the chunk embedding (a sparse ``{bucket: weight}`` vector),
which never crosses the API boundary — the service maps records to the bounded Pydantic
models in ``vault_index_models`` before returning them.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.vault_index_models import VaultIndexSnapshot, VaultSourceType

# The acceleration structure this cycle persists alongside an index: a sparse inverted index
# (postings) over the chunk embedding buckets, used for sub-linear candidate retrieval before
# the exact rerank. It is EXACT only for the sparse lexical embedding space, so it is built
# only for acceleration-eligible indexes (see ``index_is_acceleration_eligible``); dense
# (semantic) and legacy indexes keep the exact linear scan.
ACCELERATION_STRATEGY = "sparse-inverted-index"


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    id: UUID
    memory_item_id: UUID
    chunk_index: int
    start_line: int
    end_line: int
    char_count: int
    digest: str
    text: str
    embedding: dict[str, float]


@dataclass(frozen=True, slots=True)
class IndexedMemoryItem:
    id: UUID
    workspace_id: UUID
    index_id: UUID
    path: str
    source_type: VaultSourceType
    language: str | None
    digest: str
    size_bytes: int
    indexed_at: datetime
    chunks: tuple[IndexedChunk, ...]


@dataclass(frozen=True, slots=True)
class VaultItemSummary:
    """Just the memory-item metadata the architecture summary needs (no chunks)."""

    path: str
    source_type: VaultSourceType
    language: str | None
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ChunkVector:
    """A persisted chunk plus the denormalized item fields needed to rank + present it."""

    chunk_id: UUID
    memory_item_id: UUID
    path: str
    source_type: VaultSourceType
    language: str | None
    chunk_index: int
    start_line: int
    end_line: int
    text: str
    embedding: dict[str, float]


@dataclass(frozen=True, slots=True)
class VaultIndexRecord:
    snapshot: VaultIndexSnapshot
    items: tuple[IndexedMemoryItem, ...]


def index_is_acceleration_eligible(snapshot: VaultIndexSnapshot) -> bool:
    """Whether the sparse inverted index is EXACT for this index's embedding space.

    The postings acceleration is exact (and sub-linear) only for the sparse lexical embedder,
    where every chunk stores just its handful of non-zero token/bigram buckets. Dense (neural,
    ``semantic``) vectors populate every dimension, so an inverted index over them degenerates
    to a full scan while inflating storage — and legacy indexes (no embedding metadata) predate
    the embedder identity. Both keep the exact linear scan instead of a misleading acceleration.
    """
    embedding = snapshot.summary.embedding
    return embedding is not None and not embedding.semantic


def iter_chunk_postings(record: VaultIndexRecord) -> Iterator[tuple[UUID, str]]:
    """Yield ``(chunk_id, bucket)`` for every non-zero embedding bucket of every chunk.

    Yields nothing when the index is not acceleration-eligible, so callers persist postings
    only for the sparse lexical space. Storing *all* of a sparse chunk's buckets is what keeps
    candidate retrieval exact (a query bucket hits every chunk whose vector shares it).
    """
    if not index_is_acceleration_eligible(record.snapshot):
        return
    for item in record.items:
        for chunk in item.chunks:
            for bucket in chunk.embedding:
                yield chunk.id, bucket


def _chunk_vector(item: IndexedMemoryItem, chunk: IndexedChunk) -> ChunkVector:
    return ChunkVector(
        chunk_id=chunk.id,
        memory_item_id=item.id,
        path=item.path,
        source_type=item.source_type,
        language=item.language,
        chunk_index=chunk.chunk_index,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        text=chunk.text,
        embedding=chunk.embedding,
    )


class VaultIndexRepository(Protocol):
    def save_latest(self, record: VaultIndexRecord) -> None: ...

    def get_snapshot(self, workspace_id: UUID) -> VaultIndexSnapshot | None: ...

    def list_item_summaries(self, workspace_id: UUID) -> tuple[VaultItemSummary, ...]: ...

    def get_memory_item(self, memory_item_id: UUID) -> IndexedMemoryItem | None: ...

    def list_chunk_vectors(
        self, workspace_id: UUID, *, source_type: VaultSourceType | None = None
    ) -> list[ChunkVector]: ...

    def list_candidate_vectors(
        self,
        workspace_id: UUID,
        query_buckets: Sequence[str],
        *,
        source_type: VaultSourceType | None = None,
        candidate_limit: int,
    ) -> list[ChunkVector] | None:
        """Sub-linear candidate retrieval: the chunks whose embedding shares ≥1 ``query_bucket``.

        Returns the candidate ``ChunkVector`` list (to be reranked by the exact scorer), or
        ``None`` when the accelerated path does not apply for this workspace — no persisted
        postings (dense/legacy/never-built), or more than ``candidate_limit`` distinct matches
        (a query so broad the inverted index has no advantage) — so the caller falls back to the
        exact linear scan in an explicit, bounded way. An empty list means "accelerated, zero
        matches" (a correct empty result), which is distinct from ``None``.
        """
        ...


class InMemoryVaultIndexRepository:
    """Process-local latest Vault index storage, one record per workspace."""

    def __init__(self) -> None:
        self._by_workspace: dict[UUID, VaultIndexRecord] = {}
        self._items_by_id: dict[UUID, IndexedMemoryItem] = {}
        # Sparse inverted index, mirroring the SQL postings table. Present (key exists) only for
        # acceleration-eligible workspaces: workspace → bucket → chunk ids, plus chunk id →
        # candidate vector for the exact rerank. Absence ⇒ "not accelerated" (linear scan).
        self._postings: dict[UUID, dict[str, list[UUID]]] = {}
        self._candidate_vectors: dict[UUID, dict[UUID, ChunkVector]] = {}
        self._lock = RLock()

    def save_latest(self, record: VaultIndexRecord) -> None:
        with self._lock:
            workspace_id = record.snapshot.workspace_id
            previous = self._by_workspace.get(workspace_id)
            if previous is not None:
                for item in previous.items:
                    self._items_by_id.pop(item.id, None)
            self._by_workspace[workspace_id] = record
            for item in record.items:
                self._items_by_id[item.id] = item
            self._rebuild_acceleration(record)

    def _rebuild_acceleration(self, record: VaultIndexRecord) -> None:
        """Replace the workspace's inverted index atomically (drop stale, rebuild if eligible)."""
        workspace_id = record.snapshot.workspace_id
        self._postings.pop(workspace_id, None)
        self._candidate_vectors.pop(workspace_id, None)
        if not index_is_acceleration_eligible(record.snapshot):
            return
        postings: dict[str, list[UUID]] = {}
        for chunk_id, bucket in iter_chunk_postings(record):
            postings.setdefault(bucket, []).append(chunk_id)
        vectors: dict[UUID, ChunkVector] = {
            chunk.id: _chunk_vector(item, chunk)
            for item in record.items
            for chunk in item.chunks
        }
        self._postings[workspace_id] = postings
        self._candidate_vectors[workspace_id] = vectors

    def get_snapshot(self, workspace_id: UUID) -> VaultIndexSnapshot | None:
        with self._lock:
            record = self._by_workspace.get(workspace_id)
            return record.snapshot if record is not None else None

    def list_item_summaries(self, workspace_id: UUID) -> tuple[VaultItemSummary, ...]:
        with self._lock:
            record = self._by_workspace.get(workspace_id)
            if record is None:
                return ()
            return tuple(
                VaultItemSummary(
                    path=item.path,
                    source_type=item.source_type,
                    language=item.language,
                    size_bytes=item.size_bytes,
                )
                for item in record.items
            )

    def get_memory_item(self, memory_item_id: UUID) -> IndexedMemoryItem | None:
        with self._lock:
            return self._items_by_id.get(memory_item_id)

    def list_chunk_vectors(
        self, workspace_id: UUID, *, source_type: VaultSourceType | None = None
    ) -> list[ChunkVector]:
        with self._lock:
            record = self._by_workspace.get(workspace_id)
            if record is None:
                return []
            return [
                _chunk_vector(item, chunk)
                for item in record.items
                if source_type is None or item.source_type is source_type
                for chunk in item.chunks
            ]

    def list_candidate_vectors(
        self,
        workspace_id: UUID,
        query_buckets: Sequence[str],
        *,
        source_type: VaultSourceType | None = None,
        candidate_limit: int,
    ) -> list[ChunkVector] | None:
        with self._lock:
            postings = self._postings.get(workspace_id)
            if postings is None:
                return None  # not accelerated → caller falls back to the exact linear scan
            candidate_ids: set[UUID] = set()
            for bucket in query_buckets:
                candidate_ids.update(postings.get(bucket, ()))
                if len(candidate_ids) > candidate_limit:
                    return None  # too broad to accelerate → bounded linear fallback
            vectors = self._candidate_vectors[workspace_id]
            return [
                vector
                for chunk_id in candidate_ids
                if (vector := vectors.get(chunk_id)) is not None
                and (source_type is None or vector.source_type is source_type)
            ]
