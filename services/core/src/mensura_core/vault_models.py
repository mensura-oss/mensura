from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints

from mensura_core.models import ResourceModel

InventoryPath = Annotated[str, StringConstraints(min_length=1, max_length=4096)]


class VaultInventoryStatus(StrEnum):
    READY = "ready"


class VaultFileKind(StrEnum):
    TEXT = "text"
    BINARY = "binary"


class VaultNamedCount(ResourceModel):
    value: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    count: Annotated[int, Field(ge=1)]


class VaultInventorySummary(ResourceModel):
    included_file_count: Annotated[int, Field(ge=0)]
    excluded_entry_count: Annotated[int, Field(ge=0)]
    text_file_count: Annotated[int, Field(ge=0)]
    binary_file_count: Annotated[int, Field(ge=0)]
    total_size_bytes: Annotated[int, Field(ge=0)]
    extensions: list[VaultNamedCount]
    languages: list[VaultNamedCount]


class VaultInventorySnapshot(ResourceModel):
    id: UUID
    workspace_id: UUID
    status: VaultInventoryStatus = VaultInventoryStatus.READY
    built_at: AwareDatetime
    summary: VaultInventorySummary


class VaultFileInventoryItem(ResourceModel):
    path: InventoryPath
    name: Annotated[str, StringConstraints(min_length=1, max_length=1024)]
    extension: Annotated[str, StringConstraints(max_length=80)] | None
    language: Annotated[str, StringConstraints(max_length=80)] | None
    kind: VaultFileKind
    size_bytes: Annotated[int, Field(ge=0)]


class VaultFileCollection(ResourceModel):
    inventory_id: UUID
    workspace_id: UUID
    items: list[VaultFileInventoryItem]
    total: Annotated[int, Field(ge=0)]
    returned: Annotated[int, Field(ge=0)]


class VaultFilePreview(ResourceModel):
    inventory_id: UUID
    workspace_id: UUID
    file: VaultFileInventoryItem
    encoding: Literal["utf-8"] = "utf-8"
    text: str
    preview_bytes: Annotated[int, Field(ge=0, le=16 * 1024)]
    total_bytes: Annotated[int, Field(ge=0)]
    truncated: bool
