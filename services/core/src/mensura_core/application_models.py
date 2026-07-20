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

APPLICATION_ARTIFACT_SCHEMA_VERSION = "1"
APPLICATION_GUARD_OUTPUT_EXCERPT_MAX_CHARS = 2_000
APPLICATION_UNDO_CONTENT_MAX_BYTES_PER_FILE = 65_536

CommitId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")]
GuardOutputExcerpt = Annotated[
    str, StringConstraints(max_length=APPLICATION_GUARD_OUTPUT_EXCERPT_MAX_CHARS)
]
BoundedReason = Annotated[str, StringConstraints(min_length=1, max_length=500)]
UndoNote = Annotated[str, StringConstraints(min_length=1, max_length=500)]


class ApplicationStatus(StrEnum):
    APPLIED_GUARD_PASSED = "applied_guard_passed"
    APPLIED_GUARD_FAILED = "applied_guard_failed"
    APPLIED_GUARD_UNAVAILABLE = "applied_guard_unavailable"
    APPLICATION_FAILED = "application_failed"


class ApplicationTargetKind(StrEnum):
    LIVE_WORKING_TREE = "live_working_tree"


class AppliedFileReason(StrEnum):
    APPLIED = "applied"
    WRITE_FAILED = "write_failed"
    NOT_ATTEMPTED = "not_attempted"


class ApplicationUndoStrategy(StrEnum):
    RESTORE_PRIOR_CONTENT = "restore_prior_content"


class ApplicationTargetMetadata(ResourceModel):
    """Safe live-target provenance without exposing absolute filesystem paths."""

    kind: ApplicationTargetKind
    live_commit_id: CommitId
    verification_commit_id: CommitId
    head_moved_since_verification: bool


class AppliedFileResult(ResourceModel):
    path: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    change_type: ChangeProposalChangeType
    before_digest: ContextPackDigest | None
    live_before_digest: ContextPackDigest | None
    after_digest: ContextPackDigest | None
    applied_digest: ContextPackDigest | None
    applied: bool
    reason: AppliedFileReason

    @model_validator(mode="after")
    def validate_reason(self) -> "AppliedFileResult":
        if self.applied != (self.reason is AppliedFileReason.APPLIED):
            raise ValueError("applied must match the closed reason vocabulary.")
        return self


class ApplicationGuardCheck(ResourceModel):
    kind: GuardCheckKind
    status: GuardCheckStatus
    blocking: bool
    summary: Annotated[str, StringConstraints(min_length=1, max_length=240)]
    exit_code: int | None
    duration_ms: Annotated[int, Field(ge=0)]
    output_excerpt: GuardOutputExcerpt
    output_truncated: bool


class ApplicationGuardResult(ResourceModel):
    status: GuardRunStatus
    blocking: bool
    summary: GuardSummary
    checks: Annotated[list[ApplicationGuardCheck], Field(min_length=1, max_length=2)]


class ApplicationSummary(ResourceModel):
    files_total: Annotated[int, Field(ge=0)]
    created_count: Annotated[int, Field(ge=0)]
    modified_count: Annotated[int, Field(ge=0)]
    deleted_count: Annotated[int, Field(ge=0)]
    applied_count: Annotated[int, Field(ge=0)]
    failed_count: Annotated[int, Field(ge=0)]


class ApplicationUndoFileEntry(ResourceModel):
    """Bounded per-file restoration basis for a future, not-yet-built undo."""

    path: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    change_type: ChangeProposalChangeType
    prior_existed: bool
    prior_digest: ContextPackDigest | None
    prior_content: Annotated[str, StringConstraints(max_length=131_072)] | None
    prior_content_bytes: Annotated[int, Field(ge=0)]
    prior_truncated: bool
    applied_digest: ContextPackDigest | None


class ApplicationUndoMetadata(ResourceModel):
    strategy: ApplicationUndoStrategy
    note: UndoNote
    captured_at: AwareDatetime
    files: Annotated[
        tuple[ApplicationUndoFileEntry, ...],
        Field(max_length=CHANGE_PROPOSAL_MAX_FILE_CHANGES),
    ]


class ApplicationArtifact(ResourceModel):
    id: UUID
    schema_version: Literal["1"] = APPLICATION_ARTIFACT_SCHEMA_VERSION
    proposal_id: UUID
    verification_id: UUID
    run_id: UUID
    task_id: UUID
    workspace_id: UUID
    context_pack_id: ContextPackDigest
    status: ApplicationStatus
    target: ApplicationTargetMetadata
    guard: ApplicationGuardResult | None
    guard_unavailable_reason: BoundedReason | None
    file_results: Annotated[
        tuple[AppliedFileResult, ...],
        Field(min_length=1, max_length=CHANGE_PROPOSAL_MAX_FILE_CHANGES),
    ]
    summary: ApplicationSummary
    undo: ApplicationUndoMetadata
    created_at: AwareDatetime
    finished_at: AwareDatetime
    duration_ms: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def validate_outcome(self) -> "ApplicationArtifact":
        applied = sum(result.applied for result in self.file_results)
        if applied != self.summary.applied_count:
            raise ValueError("summary appliedCount must match the applied file results.")
        if self.summary.applied_count + self.summary.failed_count != self.summary.files_total:
            raise ValueError("summary counts must partition every file result.")
        if self.summary.files_total != len(self.file_results):
            raise ValueError("summary filesTotal must match the file results.")

        guard_expected = self.status in {
            ApplicationStatus.APPLIED_GUARD_PASSED,
            ApplicationStatus.APPLIED_GUARD_FAILED,
        }
        if (self.guard is not None) != guard_expected:
            raise ValueError("Guard results exist exactly when Guard executed after apply.")
        if (self.guard_unavailable_reason is not None) != (
            self.status is ApplicationStatus.APPLIED_GUARD_UNAVAILABLE
        ):
            raise ValueError("guardUnavailableReason is set exactly when Guard could not run.")

        if self.status is ApplicationStatus.APPLICATION_FAILED:
            if self.summary.failed_count == 0:
                raise ValueError("A failed application must record at least one unapplied file.")
        elif self.summary.failed_count != 0:
            raise ValueError("An applied outcome cannot record unapplied files.")

        if self.guard is not None:
            passed = self.guard.status is GuardRunStatus.PASSED
            if passed != (self.status is ApplicationStatus.APPLIED_GUARD_PASSED):
                raise ValueError("Application status must match the live Guard status.")

        if self.finished_at < self.created_at:
            raise ValueError("finishedAt cannot precede createdAt.")
        return self


class ApplicationCollection(ResourceModel):
    items: tuple[ApplicationArtifact, ...]
    total: Annotated[int, Field(ge=0)]


class ApplyChangeProposal(ResourceModel):
    verification_id: UUID
