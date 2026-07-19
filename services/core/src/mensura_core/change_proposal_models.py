from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from mensura_core.models import (
    BoundedRationale,
    BoundedSummary,
    ChangeProposalChangeType,
    ContextPackDigest,
    LanguageName,
    PromptVersion,
    ProviderId,
    ResourceModel,
)

CHANGE_PROPOSAL_SCHEMA_VERSION = "1"
CHANGE_PROPOSAL_MAX_FILE_CHANGES = 16
CHANGE_PROPOSAL_MAX_SOURCE_TEXT_BYTES = 131_072
CHANGE_PROPOSAL_MAX_STORED_TEXT_BYTES_PER_FILE = 8_192
CHANGE_PROPOSAL_MAX_STORED_TEXT_BYTES_TOTAL = 32_768


class ChangeProposalStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ChangeProposalFileChange(ResourceModel):
    path: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    change_type: ChangeProposalChangeType
    language: LanguageName | None
    before_digest: ContextPackDigest | None
    after_digest: ContextPackDigest | None
    proposed_text: str | None
    proposed_text_bytes: Annotated[
        int, Field(ge=0, le=CHANGE_PROPOSAL_MAX_STORED_TEXT_BYTES_PER_FILE)
    ]
    original_text_bytes: Annotated[int, Field(ge=0, le=CHANGE_PROPOSAL_MAX_SOURCE_TEXT_BYTES)]
    truncated: bool

    @model_validator(mode="after")
    def validate_text_metadata(self) -> "ChangeProposalFileChange":
        stored_bytes = (
            len(self.proposed_text.encode("utf-8")) if self.proposed_text is not None else 0
        )
        if stored_bytes != self.proposed_text_bytes:
            raise ValueError("proposedTextBytes must match the stored UTF-8 text.")
        if self.proposed_text_bytes > self.original_text_bytes:
            raise ValueError("Stored proposal text cannot exceed its original byte count.")
        if self.truncated != (self.proposed_text_bytes < self.original_text_bytes):
            raise ValueError("Proposal truncation metadata is inconsistent.")
        return self


class ChangeProposal(ResourceModel):
    id: UUID
    schema_version: Literal["1"] = CHANGE_PROPOSAL_SCHEMA_VERSION
    run_id: UUID
    task_id: UUID
    workspace_id: UUID
    context_pack_id: ContextPackDigest
    provider_id: ProviderId
    prompt_version: PromptVersion
    status: ChangeProposalStatus
    created_at: AwareDatetime
    reviewed_at: AwareDatetime | None = None
    summary: BoundedSummary
    rationale: BoundedRationale
    file_changes: Annotated[
        tuple[ChangeProposalFileChange, ...],
        Field(max_length=CHANGE_PROPOSAL_MAX_FILE_CHANGES),
    ]

    @model_validator(mode="after")
    def validate_review_state(self) -> "ChangeProposal":
        if self.status is ChangeProposalStatus.PROPOSED:
            valid = self.reviewed_at is None
        else:
            valid = self.reviewed_at is not None
        if not valid:
            raise ValueError("Proposal review timestamp is inconsistent with status.")
        if self.reviewed_at is not None and self.reviewed_at < self.created_at:
            raise ValueError("reviewedAt cannot precede createdAt.")
        return self


class CreateChangeProposalResponse(ResourceModel):
    proposal: ChangeProposal
    created: bool


class ChangeProposalCollection(ResourceModel):
    items: tuple[ChangeProposal, ...]
    total: Annotated[int, Field(ge=0)]
