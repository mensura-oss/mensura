from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from mensura_core.guard_models import (
    GuardCheckKind,
    GuardCheckStatus,
    GuardRunStatus,
    GuardSummary,
)
from mensura_core.models import (
    ChangeProposalChangeType,
    ContextPackDigest,
    ResourceModel,
)

UNDO_ARTIFACT_SCHEMA_VERSION = "1"
UNDO_GUARD_OUTPUT_EXCERPT_MAX_CHARS = 2_000
BoundedUndoReason = Annotated[str, StringConstraints(min_length=1, max_length=500)]
BoundedUndoGuardUnavailableReason = Annotated[str, StringConstraints(min_length=1, max_length=500)]


class UndoStatus(StrEnum):
    UNDONE_GUARD_PASSED = "undone_guard_passed"
    UNDONE_GUARD_FAILED = "undone_guard_failed"
    UNDO_REFUSED = "undo_refused"
    UNDO_FAILED = "undo_failed"


class UndoFileAction(StrEnum):
    RESTORED = "restored"
    DELETED = "deleted"
    REFUSED = "refused"
    FAILED = "failed"


class UndoGuardCheck(ResourceModel):
    kind: GuardCheckKind
    status: GuardCheckStatus
    blocking: bool
    summary: Annotated[str, StringConstraints(min_length=1, max_length=240)]
    exit_code: int | None
    duration_ms: Annotated[int, Field(ge=0)]
    output_excerpt: Annotated[
        str, StringConstraints(max_length=UNDO_GUARD_OUTPUT_EXCERPT_MAX_CHARS)
    ]
    output_truncated: bool


class UndoGuardResult(ResourceModel):
    status: GuardRunStatus
    blocking: bool
    summary: GuardSummary
    checks: Annotated[list[UndoGuardCheck], Field(min_length=1, max_length=2)]


class UndoFileOutcome(ResourceModel):
    path: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    change_type: ChangeProposalChangeType
    undone: bool
    action: UndoFileAction
    expected_applied_digest: ContextPackDigest | None
    observed_live_digest: ContextPackDigest | None
    prior_digest_restored: ContextPackDigest | None
    reason: BoundedUndoReason

    @model_validator(mode="after")
    def validate_undone_action(self) -> "UndoFileOutcome":
        if self.undone != (self.action in {UndoFileAction.RESTORED, UndoFileAction.DELETED}):
            raise ValueError("undone must be True exactly when action is restored or deleted.")
        return self


class UndoArtifact(ResourceModel):
    id: UUID
    schema_version: Literal["1"] = UNDO_ARTIFACT_SCHEMA_VERSION
    application_id: UUID
    proposal_id: UUID
    workspace_id: UUID
    status: UndoStatus
    file_outcomes: Annotated[
        tuple[UndoFileOutcome, ...], Field(min_length=0, max_length=16)
    ]
    guard: UndoGuardResult | None
    guard_unavailable_reason: BoundedUndoGuardUnavailableReason | None
    created_at: AwareDatetime
    finished_at: AwareDatetime
    duration_ms: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def validate_outcome(self) -> "UndoArtifact":
        guard_expected = self.status in {
            UndoStatus.UNDONE_GUARD_PASSED,
            UndoStatus.UNDONE_GUARD_FAILED,
        }
        if (self.guard is not None) != guard_expected:
            raise ValueError("Guard results exist exactly when Guard executed after undo.")
        if self.status is UndoStatus.UNDONE_GUARD_FAILED and self.guard is None:
            if not self.guard_unavailable_reason:
                raise ValueError(
                    "guardUnavailableReason must be set when Guard could not run after undo."
                )
        elif self.guard is not None and self.guard_unavailable_reason is not None:
            raise ValueError(
                "guardUnavailableReason must be None when Guard result is present."
            )
        if self.finished_at < self.created_at:
            raise ValueError("finishedAt cannot precede createdAt.")
        return self


class UndoCollection(ResourceModel):
    items: tuple[UndoArtifact, ...]
    total: Annotated[int, Field(ge=0)]
