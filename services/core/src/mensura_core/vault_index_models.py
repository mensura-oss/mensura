"""Domain and API models for the Vault indexing, retrieval, and summary MVP.

These sit alongside the read-only inventory models in ``vault_models.py``; the indexing
layer is additive. Chunk embeddings are an internal index artifact and are deliberately
never exposed on any API model here.
"""

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints

from mensura_core.models import ResourceModel
from mensura_core.vault_models import VaultNamedCount

IndexPath = Annotated[str, StringConstraints(min_length=1, max_length=4096)]
Sha256Digest = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
ChunkText = Annotated[str, StringConstraints(max_length=8192)]
SearchQuery = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class VaultSourceType(StrEnum):
    """How an indexed file is treated for chunking and retrieval."""

    CODE = "code"
    DOC = "doc"
    CONFIG = "config"


class VaultIndexStatus(StrEnum):
    READY = "ready"


class VaultSkipReason(StrEnum):
    EXCLUDED = "excluded"
    BINARY = "binary"
    TOO_LARGE = "too_large"
    UNSUPPORTED_TYPE = "unsupported_type"
    EMPTY = "empty"
    READ_ERROR = "read_error"


class VaultSkippedFile(ResourceModel):
    path: IndexPath
    reason: VaultSkipReason


class VaultEmbeddingInfo(ResourceModel):
    """Which embedding backend produced an index's chunk vectors.

    Recorded so search can report the retrieval mode honestly and detect a stale index (one
    built by a different backend than the one now configured). ``semantic`` is ``True`` only
    for real neural embeddings; the lexical hashing fallback reports ``False``.
    """

    backend: Annotated[str, StringConstraints(min_length=1, max_length=40)]
    model: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    dim: Annotated[int, Field(ge=0)]
    semantic: bool


class VaultIndexSummary(ResourceModel):
    memory_item_count: Annotated[int, Field(ge=0)]
    chunk_count: Annotated[int, Field(ge=0)]
    code_file_count: Annotated[int, Field(ge=0)]
    doc_file_count: Annotated[int, Field(ge=0)]
    config_file_count: Annotated[int, Field(ge=0)]
    total_size_bytes: Annotated[int, Field(ge=0)]
    skipped_count: Annotated[int, Field(ge=0)]
    skipped_by_reason: Annotated[list[VaultNamedCount], Field(max_length=16)]
    languages: Annotated[list[VaultNamedCount], Field(max_length=64)]
    skipped_sample: Annotated[list[VaultSkippedFile], Field(max_length=100)]
    # Additive + optional: absent on indexes built before this field existed (they were the
    # lexical hashing embedder). Stored inside the JSON summary column — no migration.
    embedding: VaultEmbeddingInfo | None = None


class VaultIndexSnapshot(ResourceModel):
    id: UUID
    workspace_id: UUID
    status: VaultIndexStatus = VaultIndexStatus.READY
    indexed_at: AwareDatetime
    summary: VaultIndexSummary


class VaultChunk(ResourceModel):
    id: UUID
    memory_item_id: UUID
    chunk_index: Annotated[int, Field(ge=0)]
    start_line: Annotated[int, Field(ge=1)]
    end_line: Annotated[int, Field(ge=1)]
    char_count: Annotated[int, Field(ge=0)]
    digest: Sha256Digest
    text: ChunkText


class VaultMemoryItem(ResourceModel):
    id: UUID
    workspace_id: UUID
    index_id: UUID
    path: IndexPath
    source_type: VaultSourceType
    language: Annotated[str, StringConstraints(max_length=80)] | None
    digest: Sha256Digest
    size_bytes: Annotated[int, Field(ge=0)]
    chunk_count: Annotated[int, Field(ge=0)]
    indexed_at: AwareDatetime


class VaultMemoryItemDetail(ResourceModel):
    item: VaultMemoryItem
    chunks: Annotated[list[VaultChunk], Field(max_length=200)]


class VaultSearchHit(ResourceModel):
    memory_item_id: UUID
    chunk_id: UUID
    path: IndexPath
    source_type: VaultSourceType
    language: Annotated[str, StringConstraints(max_length=80)] | None
    chunk_index: Annotated[int, Field(ge=0)]
    start_line: Annotated[int, Field(ge=1)]
    end_line: Annotated[int, Field(ge=1)]
    score: Annotated[float, Field(ge=0.0)]
    snippet: Annotated[str, StringConstraints(max_length=600)]


class VaultSearchResponse(ResourceModel):
    workspace_id: UUID
    index_id: UUID
    query: SearchQuery
    strategy: str = "lexical-vector-cosine"
    total: Annotated[int, Field(ge=0)]
    returned: Annotated[int, Field(ge=0)]
    hits: Annotated[list[VaultSearchHit], Field(max_length=50)]


class VaultModuleSummary(ResourceModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    path: Annotated[str, StringConstraints(max_length=4096)]
    file_count: Annotated[int, Field(ge=0)]
    total_size_bytes: Annotated[int, Field(ge=0)]
    primary_language: Annotated[str, StringConstraints(max_length=80)] | None


class VaultArchitectureSummary(ResourceModel):
    workspace_id: UUID
    index_id: UUID
    generated_at: AwareDatetime
    file_count: Annotated[int, Field(ge=0)]
    code_file_count: Annotated[int, Field(ge=0)]
    doc_file_count: Annotated[int, Field(ge=0)]
    config_file_count: Annotated[int, Field(ge=0)]
    total_size_bytes: Annotated[int, Field(ge=0)]
    languages: Annotated[list[VaultNamedCount], Field(max_length=32)]
    modules: Annotated[list[VaultModuleSummary], Field(max_length=50)]
    technologies: Annotated[list[str], Field(max_length=32)]
    entry_points: Annotated[list[str], Field(max_length=32)]


class VaultIndexRequest(ResourceModel):
    workspace_id: UUID


class VaultSummarizeRequest(ResourceModel):
    workspace_id: UUID


class VaultSearchRequest(ResourceModel):
    workspace_id: UUID
    query: SearchQuery
    limit: Annotated[int, Field(ge=1, le=50)] = 10
    source_type: VaultSourceType | None = None
