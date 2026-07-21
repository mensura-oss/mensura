from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints

from mensura_core.models import ResourceModel

BACKUP_ARTIFACT_SCHEMA_VERSION = "1"
BoundedLabel = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)
]
BoundedErrorMessage = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
BoundedStoragePath = Annotated[str, StringConstraints(min_length=1, max_length=512)]


class BackupStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class BackupArtifact(ResourceModel):
    id: UUID
    schema_version: Literal["1"] = BACKUP_ARTIFACT_SCHEMA_VERSION
    created_at: AwareDatetime
    db_version: str | None
    file_size_bytes: Annotated[int, Field(ge=0)]
    sha256_hex: Annotated[str, StringConstraints(min_length=0, max_length=64)]
    storage_path: BoundedStoragePath
    status: BackupStatus
    label: BoundedLabel | None = None
    error_message: BoundedErrorMessage | None = None


class BackupCollection(ResourceModel):
    items: tuple[BackupArtifact, ...]
    total: Annotated[int, Field(ge=0)]
