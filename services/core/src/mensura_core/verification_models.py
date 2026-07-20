from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from mensura_core.change_proposal_models import CHANGE_PROPOSAL_MAX_FILE_CHANGES
from mensura_core.guard_models import GuardCheckKind, GuardCheckStatus, GuardRunStatus, GuardSummary
from mensura_core.models import (
    ChangeProposalChangeType,
    ContextPackDigest,
    ResourceModel,
)

PROPOSAL_VERIFICATION_SCHEMA_VERSION = "1"
VERIFICATION_GUARD_OUTPUT_EXCERPT_MAX_CHARS = 2_000

CommitId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")]
GuardOutputExcerpt = Annotated[
    str, StringConstraints(max_length=VERIFICATION_GUARD_OUTPUT_EXCERPT_MAX_CHARS)
]


class ProposalVerificationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class ProposalVerificationOutcome(StrEnum):
    SANDBOX_VERIFIED = "sandbox_verified"
    GUARD_FAILED = "guard_failed"
    MATERIALIZATION_FAILED = "materialization_failed"


class VerificationSandboxKind(StrEnum):
    GIT_WORKTREE = "git_worktree"


class FileVerificationReason(StrEnum):
    APPLIED = "applied"
    CREATE_TARGET_EXISTS = "create_target_exists"
    TARGET_MISSING = "target_missing"
    TARGET_NOT_A_FILE = "target_not_a_file"
    BEFORE_CONTENT_MISMATCH = "before_content_mismatch"
    UNSAFE_PATH = "unsafe_path"


class VerificationSandboxMetadata(ResourceModel):
    """Safe sandbox provenance without temporary filesystem paths."""

    kind: VerificationSandboxKind
    commit_id: CommitId
    cleanup_completed: bool


class FileVerificationResult(ResourceModel):
    path: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    change_type: ChangeProposalChangeType
    before_digest: ContextPackDigest | None
    after_digest: ContextPackDigest | None
    sandbox_digest: ContextPackDigest | None
    applied_in_sandbox: bool
    reason: FileVerificationReason

    @model_validator(mode="after")
    def validate_reason(self) -> "FileVerificationResult":
        if self.applied_in_sandbox != (self.reason is FileVerificationReason.APPLIED):
            raise ValueError("appliedInSandbox must match the closed reason vocabulary.")
        return self


class VerificationGuardCheck(ResourceModel):
    kind: GuardCheckKind
    status: GuardCheckStatus
    blocking: bool
    summary: Annotated[str, StringConstraints(min_length=1, max_length=240)]
    exit_code: int | None
    duration_ms: Annotated[int, Field(ge=0)]
    output_excerpt: GuardOutputExcerpt
    output_truncated: bool


class VerificationGuardResult(ResourceModel):
    status: GuardRunStatus
    blocking: bool
    summary: GuardSummary
    checks: Annotated[list[VerificationGuardCheck], Field(min_length=1, max_length=2)]


class SafeDiffMetadata(ResourceModel):
    files_total: Annotated[int, Field(ge=0)]
    created_count: Annotated[int, Field(ge=0)]
    modified_count: Annotated[int, Field(ge=0)]
    deleted_count: Annotated[int, Field(ge=0)]
    applied_count: Annotated[int, Field(ge=0)]
    unapplied_count: Annotated[int, Field(ge=0)]
    proposed_bytes_total: Annotated[int, Field(ge=0)]


class ProposalVerification(ResourceModel):
    id: UUID
    schema_version: Literal["1"] = PROPOSAL_VERIFICATION_SCHEMA_VERSION
    proposal_id: UUID
    run_id: UUID
    task_id: UUID
    workspace_id: UUID
    context_pack_id: ContextPackDigest
    status: ProposalVerificationStatus
    outcome: ProposalVerificationOutcome
    sandbox: VerificationSandboxMetadata
    guard: VerificationGuardResult | None
    file_results: Annotated[
        tuple[FileVerificationResult, ...],
        Field(max_length=CHANGE_PROPOSAL_MAX_FILE_CHANGES),
    ]
    safe_diff: SafeDiffMetadata
    created_at: AwareDatetime
    finished_at: AwareDatetime
    duration_ms: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def validate_outcome(self) -> "ProposalVerification":
        if (self.status is ProposalVerificationStatus.PASSED) != (
            self.outcome is ProposalVerificationOutcome.SANDBOX_VERIFIED
        ):
            raise ValueError("Verification status must match the closed outcome.")
        if (self.outcome is ProposalVerificationOutcome.MATERIALIZATION_FAILED) != (
            self.guard is None
        ):
            raise ValueError("Guard results exist exactly when materialization completed.")
        if self.finished_at < self.created_at:
            raise ValueError("finishedAt cannot precede createdAt.")
        return self


class ProposalVerificationCollection(ResourceModel):
    items: tuple[ProposalVerification, ...]
    total: Annotated[int, Field(ge=0)]
