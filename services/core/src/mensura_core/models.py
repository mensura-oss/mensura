from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
RootPath = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10_000)]


class ApiModel(BaseModel):
    """Base for camelCase JSON contracts with strict, documented fields."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )


class ResourceModel(ApiModel):
    """Immutable API resource stored by the initial in-memory adapter."""

    model_config = ConfigDict(frozen=True)


class AgentRole(StrEnum):
    ARCHITECT = "architect"
    RESEARCH = "research"
    CODER = "coder"
    REFACTOR = "refactor"
    TEST = "test"
    REVIEWER = "reviewer"
    SECURITY = "security"
    DEVOPS = "devops"
    DOCS = "docs"
    RELEASE = "release"


class TaskStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunStatus(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    EXECUTING = "executing"
    CHECKING = "checking"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HealthResponse(ApiModel):
    status: Literal["ok"]
    service: Literal["mensura-core"]
    version: str


class WorkspaceCreate(ApiModel):
    name: Name
    root_path: RootPath


class Workspace(ResourceModel):
    id: UUID
    name: Name
    root_path: RootPath
    created_at: AwareDatetime
    updated_at: AwareDatetime


class WorkspaceCollection(ApiModel):
    items: list[Workspace]
    total: Annotated[int, Field(ge=0)]


class TaskCreate(ApiModel):
    workspace_id: UUID
    title: Title
    description: Description = ""
    assigned_role: AgentRole | None = None


class Task(ResourceModel):
    id: UUID
    workspace_id: UUID
    title: Title
    description: Description
    status: TaskStatus
    assigned_role: AgentRole | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class Run(ResourceModel):
    id: UUID
    task_id: UUID
    status: RunStatus
    started_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime


def ensure_utc_timestamp(value: datetime) -> datetime:
    """Fail fast if an internal caller attempts to emit a naive timestamp."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("API timestamps must be timezone-aware")
    return value
