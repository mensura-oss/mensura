"""Vault indexing, retrieval, and architecture-summary service."""

from collections import Counter
from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from mensura_core.exceptions import (
    ResourceNotFoundError,
    VaultIndexNotBuiltError,
    VaultMemoryItemNotFoundError,
)
from mensura_core.models import Workspace
from mensura_core.repositories import CoreRepository
from mensura_core.vault_index_models import (
    VaultArchitectureSummary,
    VaultChunk,
    VaultIndexSnapshot,
    VaultIndexSummary,
    VaultMemoryItem,
    VaultMemoryItemDetail,
    VaultSearchHit,
    VaultSearchResponse,
    VaultSourceType,
)
from mensura_core.vault_index_repositories import (
    IndexedMemoryItem,
    VaultIndexRecord,
    VaultIndexRepository,
)
from mensura_core.vault_indexer import (
    BuiltVaultIndex,
    Embedder,
    HashingEmbedder,
    VaultIndexBuilder,
    cosine_similarity,
    utc_now,
)
from mensura_core.vault_models import VaultNamedCount
from mensura_core.vault_summary import summarize_architecture

IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]

SUBSTRING_BOOST = 0.5
SNIPPET_MAX_CHARS = 400
SUMMARY_LANGUAGE_LIMIT = 64
SUMMARY_SKIP_REASON_LIMIT = 16


class VaultIndexService:
    def __init__(
        self,
        core_repository: CoreRepository,
        indexer: VaultIndexBuilder,
        index_repository: VaultIndexRepository,
        *,
        embedder: Embedder | None = None,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
    ) -> None:
        self._core_repository = core_repository
        self._indexer = indexer
        self._index_repository = index_repository
        self._embedder = embedder or HashingEmbedder()
        self._id_factory = id_factory
        self._clock = clock

    def index_workspace(self, workspace_id: UUID) -> VaultIndexSnapshot:
        workspace = self._require_workspace(workspace_id)
        index_id = self._id_factory()
        built = self._indexer.build(
            workspace.root_path, workspace_id=workspace.id, index_id=index_id
        )
        snapshot = VaultIndexSnapshot(
            id=index_id,
            workspace_id=workspace.id,
            indexed_at=self._clock(),
            summary=self._build_summary(built),
        )
        self._index_repository.save_latest(VaultIndexRecord(snapshot, built.items))
        return snapshot

    def get_index(self, workspace_id: UUID) -> VaultIndexSnapshot:
        self._require_workspace(workspace_id)
        return self._require_snapshot(workspace_id)

    def search(
        self,
        workspace_id: UUID,
        *,
        query: str,
        limit: int,
        source_type: VaultSourceType | None,
    ) -> VaultSearchResponse:
        self._require_workspace(workspace_id)
        snapshot = self._require_snapshot(workspace_id)
        query_vector = self._embedder.embed(query)
        needle = query.casefold().strip()
        vectors = self._index_repository.list_chunk_vectors(workspace_id, source_type=source_type)
        scored = []
        for vector in vectors:
            score = cosine_similarity(query_vector, vector.embedding)
            if needle and needle in vector.text.casefold():
                score += SUBSTRING_BOOST
            if score > 0.0:
                scored.append((score, vector))
        scored.sort(key=lambda pair: (-pair[0], pair[1].path, pair[1].chunk_index))
        top = scored[:limit]
        hits = [
            VaultSearchHit(
                memory_item_id=vector.memory_item_id,
                chunk_id=vector.chunk_id,
                path=vector.path,
                source_type=vector.source_type,
                language=vector.language,
                chunk_index=vector.chunk_index,
                start_line=vector.start_line,
                end_line=vector.end_line,
                score=round(score, 6),
                snippet=_snippet(vector.text),
            )
            for score, vector in top
        ]
        return VaultSearchResponse(
            workspace_id=workspace_id,
            index_id=snapshot.id,
            query=query,
            total=len(scored),
            returned=len(hits),
            hits=hits,
        )

    def get_memory_item(self, memory_item_id: UUID) -> VaultMemoryItemDetail:
        item = self._index_repository.get_memory_item(memory_item_id)
        if item is None:
            raise VaultMemoryItemNotFoundError(memory_item_id)
        return VaultMemoryItemDetail(
            item=_to_memory_item_model(item),
            chunks=[
                VaultChunk(
                    id=chunk.id,
                    memory_item_id=chunk.memory_item_id,
                    chunk_index=chunk.chunk_index,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    char_count=chunk.char_count,
                    digest=chunk.digest,
                    text=chunk.text,
                )
                for chunk in item.chunks
            ],
        )

    def summarize(self, workspace_id: UUID) -> VaultArchitectureSummary:
        self._require_workspace(workspace_id)
        snapshot = self._require_snapshot(workspace_id)
        items = self._index_repository.list_item_summaries(workspace_id)
        return summarize_architecture(
            items,
            workspace_id=workspace_id,
            index_id=snapshot.id,
            generated_at=self._clock(),
        )

    def _build_summary(self, built: BuiltVaultIndex) -> VaultIndexSummary:
        items = built.items
        language_counts: Counter[str] = Counter(item.language for item in items if item.language)
        return VaultIndexSummary(
            memory_item_count=len(items),
            chunk_count=sum(len(item.chunks) for item in items),
            code_file_count=sum(1 for item in items if item.source_type is VaultSourceType.CODE),
            doc_file_count=sum(1 for item in items if item.source_type is VaultSourceType.DOC),
            config_file_count=sum(
                1 for item in items if item.source_type is VaultSourceType.CONFIG
            ),
            total_size_bytes=sum(item.size_bytes for item in items),
            skipped_count=sum(built.skipped_counts.values()),
            skipped_by_reason=_named_counts(built.skipped_counts, SUMMARY_SKIP_REASON_LIMIT),
            languages=_named_counts(language_counts, SUMMARY_LANGUAGE_LIMIT),
            skipped_sample=list(built.skipped_sample),
        )

    def _require_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self._core_repository.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace", workspace_id)
        return workspace

    def _require_snapshot(self, workspace_id: UUID) -> VaultIndexSnapshot:
        snapshot = self._index_repository.get_snapshot(workspace_id)
        if snapshot is None:
            raise VaultIndexNotBuiltError(workspace_id)
        return snapshot


def _to_memory_item_model(item: IndexedMemoryItem) -> VaultMemoryItem:
    return VaultMemoryItem(
        id=item.id,
        workspace_id=item.workspace_id,
        index_id=item.index_id,
        path=item.path,
        source_type=item.source_type,
        language=item.language,
        digest=item.digest,
        size_bytes=item.size_bytes,
        chunk_count=len(item.chunks),
        indexed_at=item.indexed_at,
    )


def _snippet(text: str) -> str:
    return text.strip()[:SNIPPET_MAX_CHARS]


def _named_counts(counts: dict[str, int], limit: int) -> list[VaultNamedCount]:
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [VaultNamedCount(value=value, count=count) for value, count in ordered[:limit]]
