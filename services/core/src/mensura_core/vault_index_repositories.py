"""Internal index records and the Vault index repository boundary.

The dataclasses here carry the chunk embedding (a sparse ``{bucket: weight}`` vector),
which never crosses the API boundary — the service maps records to the bounded Pydantic
models in ``vault_index_models`` before returning them.
"""

from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.vault_index_models import VaultIndexSnapshot, VaultSourceType


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


class VaultIndexRepository(Protocol):
    def save_latest(self, record: VaultIndexRecord) -> None: ...

    def get_snapshot(self, workspace_id: UUID) -> VaultIndexSnapshot | None: ...

    def list_item_summaries(self, workspace_id: UUID) -> tuple[VaultItemSummary, ...]: ...

    def get_memory_item(self, memory_item_id: UUID) -> IndexedMemoryItem | None: ...

    def list_chunk_vectors(
        self, workspace_id: UUID, *, source_type: VaultSourceType | None = None
    ) -> list[ChunkVector]: ...


class InMemoryVaultIndexRepository:
    """Process-local latest Vault index storage, one record per workspace."""

    def __init__(self) -> None:
        self._by_workspace: dict[UUID, VaultIndexRecord] = {}
        self._items_by_id: dict[UUID, IndexedMemoryItem] = {}
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
            vectors: list[ChunkVector] = []
            for item in record.items:
                if source_type is not None and item.source_type is not source_type:
                    continue
                for chunk in item.chunks:
                    vectors.append(
                        ChunkVector(
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
                    )
            return vectors
