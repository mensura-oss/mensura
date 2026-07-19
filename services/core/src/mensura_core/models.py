from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    model_validator,
)
from pydantic.alias_generators import to_camel

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
RootPath = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10_000)]
BoundedSummary = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]
BoundedRationale = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
BoundedMessage = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
]
ProviderIdentifier = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
ProviderVersion = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
]
ModelIdentifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
LanguageName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
ContextPackDigest = Annotated[
    str,
    StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$"),
]


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
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProviderId(StrEnum):
    DETERMINISTIC = "mensura.builtin"
    OPENAI = "openai"


class ProviderKind(StrEnum):
    DETERMINISTIC = "deterministic"
    REAL = "real"


class PromptVersion(StrEnum):
    REVIEW_V1 = "review.v1"
    REVIEW_V2 = "review.v2"


class ChangeProposalChangeType(StrEnum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


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


class RunCreate(ApiModel):
    context_pack_id: ContextPackDigest


class RunExecute(ApiModel):
    provider_id: ProviderIdentifier


class OpenAIProviderConfigure(ApiModel):
    api_key: Annotated[SecretStr, Field(min_length=20, max_length=512)]
    model: ModelIdentifier


class ProviderDescriptor(ResourceModel):
    id: ProviderId
    name: Name
    kind: ProviderKind
    configured: bool
    model: ModelIdentifier | None
    prompt_version: PromptVersion


class ProviderCollection(ApiModel):
    items: list[ProviderDescriptor]
    total: Annotated[int, Field(ge=0)]


class RunContextPackReference(ResourceModel):
    id: ContextPackDigest
    workspace_id: UUID
    inventory_id: UUID
    schema_version: Literal["1"]
    file_count: Annotated[int, Field(ge=0)]
    total_file_bytes: Annotated[int, Field(ge=0)]
    total_preview_bytes: Annotated[int, Field(ge=0)]


class RunProviderMetadata(ResourceModel):
    provider_id: ProviderId
    provider_kind: ProviderKind
    adapter_id: ProviderIdentifier
    adapter_version: ProviderVersion
    model: ModelIdentifier | None
    prompt_version: PromptVersion


class RunExecutionContextSummary(ResourceModel):
    context_pack_id: ContextPackDigest
    inventory_id: UUID
    file_count: Annotated[int, Field(ge=0)]
    text_file_count: Annotated[int, Field(ge=0)]
    binary_file_count: Annotated[int, Field(ge=0)]
    total_file_bytes: Annotated[int, Field(ge=0)]
    total_preview_bytes: Annotated[int, Field(ge=0)]
    truncated_text_file_count: Annotated[int, Field(ge=0)]
    languages: Annotated[tuple[LanguageName, ...], Field(max_length=32)]


class ChangeProposalDraftFileChange(ResourceModel):
    path: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    change_type: ChangeProposalChangeType
    language: LanguageName | None
    proposed_text: Annotated[str, StringConstraints(max_length=32_768)] | None


class ChangeProposalDraft(ResourceModel):
    summary: BoundedSummary
    rationale: BoundedRationale
    file_changes: Annotated[tuple[ChangeProposalDraftFileChange, ...], Field(max_length=16)]


class RunExecutionResult(ResourceModel):
    schema_version: Literal["2"] = "2"
    task_summary: BoundedSummary
    interpreted_intent: BoundedSummary
    context: RunExecutionContextSummary
    warnings: Annotated[tuple[BoundedMessage, ...], Field(max_length=8)]
    recommended_next_steps: Annotated[tuple[BoundedMessage, ...], Field(min_length=1, max_length=8)]
    proposal_draft: ChangeProposalDraft


class RunExecutionFailureCode(StrEnum):
    PROVIDER_EXECUTION_FAILED = "provider_execution_failed"
    PROVIDER_CREDENTIALS_INVALID = "provider_credentials_invalid"
    PROVIDER_UPSTREAM_FAILED = "provider_upstream_failed"
    STRUCTURED_RESULT_INVALID = "structured_result_invalid"


class RunExecutionFailure(ResourceModel):
    code: RunExecutionFailureCode
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class RunExecution(ResourceModel):
    provider: RunProviderMetadata
    duration_ms: Annotated[int, Field(ge=0, le=86_400_000)] | None = None
    result: RunExecutionResult | None = None
    failure: RunExecutionFailure | None = None


class Run(ResourceModel):
    id: UUID
    task_id: UUID
    context_pack_id: ContextPackDigest
    context_pack: RunContextPackReference
    status: RunStatus
    execution: RunExecution | None = None
    started_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @model_validator(mode="after")
    def validate_execution_state(self) -> "Run":
        if self.status is RunStatus.QUEUED:
            valid = self.execution is None and self.started_at is None and self.finished_at is None
        elif self.status is RunStatus.RUNNING:
            valid = (
                self.execution is not None
                and self.execution.duration_ms is None
                and self.execution.result is None
                and self.execution.failure is None
                and self.started_at is not None
                and self.finished_at is None
            )
        elif self.status is RunStatus.SUCCEEDED:
            valid = (
                self.execution is not None
                and self.execution.duration_ms is not None
                and self.execution.result is not None
                and self.execution.failure is None
                and self.started_at is not None
                and self.finished_at is not None
            )
        else:
            valid = (
                self.execution is not None
                and self.execution.duration_ms is not None
                and self.execution.result is None
                and self.execution.failure is not None
                and self.started_at is not None
                and self.finished_at is not None
            )
        if not valid:
            raise ValueError(f"Run fields are inconsistent with status '{self.status}'.")
        if (
            self.started_at is not None
            and self.finished_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError("Run finishedAt cannot precede startedAt.")
        return self


def ensure_utc_timestamp(value: datetime) -> datetime:
    """Fail fast if an internal caller attempts to emit a naive timestamp."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("API timestamps must be timezone-aware")
    return value
