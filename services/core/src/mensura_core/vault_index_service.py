"""Vault indexing, retrieval, and architecture-summary service."""

from collections import Counter
from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from mensura_core.exceptions import (
    ResourceNotFoundError,
    VaultEmbeddingBackendUnavailableError,
    VaultIndexNotBuiltError,
    VaultMemoryItemNotFoundError,
)
from mensura_core.models import Workspace
from mensura_core.repositories import CoreRepository
from mensura_core.vault_embedding import (
    HASHING_BACKEND,
    Embedder,
    EmbedderInfo,
    EmbeddingBackendError,
    HashingEmbedder,
    cosine_similarity,
)
from mensura_core.vault_index_models import (
    VaultArchitectureSummary,
    VaultChunk,
    VaultEmbeddingInfo,
    VaultIndexSnapshot,
    VaultIndexSummary,
    VaultMemoryItem,
    VaultMemoryItemDetail,
    VaultSearchHit,
    VaultSearchResponse,
    VaultSourceType,
)
from mensura_core.vault_index_repositories import (
    ChunkVector,
    IndexedMemoryItem,
    VaultIndexRecord,
    VaultIndexRepository,
)
from mensura_core.vault_indexer import (
    BuiltVaultIndex,
    VaultIndexBuilder,
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

# Search strategy labels reported honestly in the response so a caller always knows the mode.
STRATEGY_LEXICAL = "lexical-vector-cosine"
STRATEGY_LEXICAL_FALLBACK = "lexical-fallback:reindex-required"


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
        # Always-available offline lexical embedder for the honest degraded path when a stored
        # index was built by a different backend than the one configured now (see `search`).
        self._lexical = HashingEmbedder()
        self._id_factory = id_factory
        self._clock = clock

    def index_workspace(self, workspace_id: UUID) -> VaultIndexSnapshot:
        workspace = self._require_workspace(workspace_id)
        index_id = self._id_factory()
        try:
            built = self._indexer.build(
                workspace.root_path, workspace_id=workspace.id, index_id=index_id
            )
        except EmbeddingBackendError as error:
            # Fail clearly rather than persist a partially-embedded (mixed-space) index.
            raise VaultEmbeddingBackendUnavailableError(self._embedder.info.model) from error
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
        needle = query.casefold().strip()
        vectors = self._index_repository.list_chunk_vectors(workspace_id, source_type=source_type)

        # Rank by embedding similarity (primary) when the currently configured embedder produces
        # vectors in the SAME space as the stored index; keep the small exact-substring boost as
        # a secondary re-rank. If the index was built by a different backend (e.g. a semantic
        # index queried after the Ollama backend went down, or an old lexical index queried with
        # a semantic backend now on), the stored vectors are in an incompatible space — never
        # score across spaces. Instead degrade honestly to a lexical re-rank over the stored
        # chunk text and report a "re-index required" strategy.
        current = self._embedder.info
        query_vector: dict[str, float] | None = None
        if _index_is_compatible(snapshot.summary.embedding, current):
            try:
                query_vector = self._embedder.embed(query)
            except EmbeddingBackendError:
                query_vector = None  # backend lost after indexing → lexical fallback below

        if query_vector is not None:
            strategy = _strategy_for(current)
            scored = _score_vectors(vectors, query_vector, needle, lambda vector: vector.embedding)
        else:
            strategy = STRATEGY_LEXICAL_FALLBACK
            lexical_query = self._lexical.embed(query)
            scored = _score_vectors(
                vectors, lexical_query, needle, lambda vector: self._lexical.embed(vector.text)
            )

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
            strategy=strategy,
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
            embedding=_embedding_info(built.embedder_info),
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


def _index_is_compatible(stored: VaultEmbeddingInfo | None, current: EmbedderInfo) -> bool:
    """Whether stored vectors and a fresh query vector live in the same (comparable) space."""
    if stored is None:
        # Legacy index built before embedder metadata existed — it was the lexical hashing
        # embedder, so it is comparable only with a lexical embedder now.
        return current.backend == HASHING_BACKEND
    return (stored.backend, stored.model, stored.dim) == (
        current.backend,
        current.model,
        current.dim,
    )


def _strategy_for(info: EmbedderInfo) -> str:
    if info.semantic:
        return f"semantic-cosine:{info.backend}/{info.model}"
    return STRATEGY_LEXICAL


def _score_vectors(
    vectors: list[ChunkVector],
    query_vector: dict[str, float],
    needle: str,
    chunk_vector: Callable[[ChunkVector], dict[str, float]],
) -> list[tuple[float, ChunkVector]]:
    """Rank chunks by cosine similarity (primary), with an exact-substring boost (secondary).

    Similarity is clamped to ``>= 0`` before the boost so the score honors the API model's
    non-negative constraint (real neural cosine can be slightly negative for unrelated text).
    """
    scored: list[tuple[float, ChunkVector]] = []
    for vector in vectors:
        score = max(0.0, cosine_similarity(query_vector, chunk_vector(vector)))
        if needle and needle in vector.text.casefold():
            score += SUBSTRING_BOOST
        if score > 0.0:
            scored.append((score, vector))
    return scored


def _embedding_info(info: EmbedderInfo) -> VaultEmbeddingInfo:
    return VaultEmbeddingInfo(
        backend=info.backend, model=info.model, dim=info.dim, semantic=info.semantic
    )


def _snippet(text: str) -> str:
    return text.strip()[:SNIPPET_MAX_CHARS]


def _named_counts(counts: dict[str, int], limit: int) -> list[VaultNamedCount]:
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [VaultNamedCount(value=value, count=count) for value, count in ordered[:limit]]
