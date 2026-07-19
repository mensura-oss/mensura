from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from mensura_core.models import ApiModel, ResourceModel
from mensura_core.vault_models import VaultFileKind

CONTEXT_PACK_SCHEMA_VERSION = "1"
ContextPackDigest = Annotated[
    str,
    StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$"),
]
ContextPackPath = Annotated[str, StringConstraints(min_length=1, max_length=4096)]


class ContextPackLimits(ResourceModel):
    max_files: Annotated[int, Field(ge=1)]
    max_preview_bytes_per_file: Annotated[int, Field(ge=1)]
    max_total_preview_bytes: Annotated[int, Field(ge=1)]


class ContextPackFileEntry(ResourceModel):
    path: ContextPackPath
    name: Annotated[str, StringConstraints(min_length=1, max_length=1024)]
    extension: Annotated[str, StringConstraints(max_length=80)] | None
    language: Annotated[str, StringConstraints(max_length=80)] | None
    kind: VaultFileKind
    size_bytes: Annotated[int, Field(ge=0)]
    content_digest: ContextPackDigest
    capture_mode: Literal["text_preview", "metadata_only"]
    encoding: Literal["utf-8"] | None
    preview_text: str | None
    preview_bytes: Annotated[int, Field(ge=0)]
    total_bytes: Annotated[int, Field(ge=0)]
    truncated: bool


class ContextPackFileSummary(ResourceModel):
    file_count: Annotated[int, Field(ge=0)]
    text_file_count: Annotated[int, Field(ge=0)]
    binary_file_count: Annotated[int, Field(ge=0)]
    total_file_bytes: Annotated[int, Field(ge=0)]
    total_preview_bytes: Annotated[int, Field(ge=0)]
    truncated_text_file_count: Annotated[int, Field(ge=0)]


class ContextPackSummary(ResourceModel):
    id: ContextPackDigest
    digest: ContextPackDigest
    workspace_id: UUID
    inventory_id: UUID
    schema_version: Literal["1"] = CONTEXT_PACK_SCHEMA_VERSION
    summary: ContextPackFileSummary


class ContextPackManifest(ContextPackSummary):
    limits: ContextPackLimits
    files: tuple[ContextPackFileEntry, ...]


class CreateContextPackRequest(ApiModel):
    paths: Annotated[list[ContextPackPath], Field(min_length=1, max_length=500)]


class CreateContextPackResponse(ApiModel):
    context_pack: ContextPackManifest
    created: bool


class ContextPackCollection(ApiModel):
    items: list[ContextPackSummary]
    total: Annotated[int, Field(ge=0)]
