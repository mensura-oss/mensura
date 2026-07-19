from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from mensura_core.models import ApiModel


class RepositoryChangeType(StrEnum):
    ADDED = "added"
    COPIED = "copied"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    TYPE_CHANGED = "typeChanged"
    UNMERGED = "unmerged"
    UNTRACKED = "untracked"


class RepositoryDiffMetadata(ApiModel):
    path: str
    change_type: RepositoryChangeType
    staged: bool
    old_path: str | None = None


class RepositoryInspection(ApiModel):
    branch: str | None
    is_dirty: bool
    staged_count: Annotated[int, Field(ge=0)]
    unstaged_count: Annotated[int, Field(ge=0)]
    untracked_count: Annotated[int, Field(ge=0)]
    changed_paths_count: Annotated[int, Field(ge=0)]
    diff_metadata: list[RepositoryDiffMetadata]


class RepositorySummary(RepositoryInspection):
    workspace_id: UUID
    is_repository: Literal[True] = True
