from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from mensura_core.models import ResourceModel

JOB_SCHEMA_VERSION = "1"
JOB_LAST_ERROR_MAX_CHARS = 2_000

BoundedJobLabel = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)
]
BoundedJobError = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=JOB_LAST_ERROR_MAX_CHARS)
]
BoundedResultType = Annotated[str, StringConstraints(min_length=1, max_length=40)]


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobType(StrEnum):
    PROPOSAL_VERIFICATION = "proposal_verification"
    APPLICATION_APPLY = "application_apply"
    APPLICATION_UNDO = "application_undo"
    BACKUP_CREATE = "backup_create"


class JobTargetType(StrEnum):
    CHANGE_PROPOSAL = "change_proposal"
    APPLICATION = "application"
    DATABASE = "database"


class JobPayload(ResourceModel):
    """Bounded reference data — identifiers and a label only, never artifact bodies."""

    proposal_id: UUID | None = None
    verification_id: UUID | None = None
    application_id: UUID | None = None
    label: BoundedJobLabel | None = None


class Job(ResourceModel):
    id: UUID
    schema_version: Literal["1"] = JOB_SCHEMA_VERSION
    job_type: JobType
    target_entity_type: JobTargetType
    target_entity_id: UUID | None
    workspace_id: UUID | None
    status: JobStatus
    attempt_count: Annotated[int, Field(ge=0)]
    payload: JobPayload
    result_entity_type: BoundedResultType | None
    result_entity_id: UUID | None
    last_error: BoundedJobError | None
    created_at: AwareDatetime
    started_at: AwareDatetime | None
    finished_at: AwareDatetime | None
    retry_of_job_id: UUID | None = None
    root_job_id: UUID | None = None
    retry_eligible: bool = True
    retry_count: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "Job":
        started = self.status in {JobStatus.RUNNING, JobStatus.SUCCEEDED, JobStatus.FAILED}
        terminal = self.status in {JobStatus.SUCCEEDED, JobStatus.FAILED}
        if started and self.started_at is None:
            raise ValueError("startedAt must be set once a job has started running.")
        if terminal and self.finished_at is None:
            raise ValueError("finishedAt must be set for a terminal job.")
        if self.status is JobStatus.QUEUED and (
            self.started_at is not None or self.finished_at is not None
        ):
            raise ValueError("A queued job has no start or finish timestamps.")
        if self.status is JobStatus.SUCCEEDED:
            if self.result_entity_id is None or self.result_entity_type is None:
                raise ValueError("A succeeded job must reference its produced artifact.")
            if self.last_error is not None:
                raise ValueError("A succeeded job has no lastError.")
        if self.status is JobStatus.FAILED and not self.last_error:
            raise ValueError("A failed job must record a bounded lastError summary.")
        if self.started_at is not None and self.started_at < self.created_at:
            raise ValueError("startedAt cannot precede createdAt.")
        if (
            self.finished_at is not None
            and self.started_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError("finishedAt cannot precede startedAt.")
        return self

    @model_validator(mode="after")
    def validate_target_and_payload(self) -> "Job":
        if self.job_type is JobType.BACKUP_CREATE:
            if self.target_entity_type is not JobTargetType.DATABASE:
                raise ValueError("A backup job must target the database.")
        elif self.target_entity_id is None:
            raise ValueError("A non-backup job must reference a target entity id.")
        if (
            self.job_type in {JobType.PROPOSAL_VERIFICATION, JobType.APPLICATION_APPLY}
            and self.payload.proposal_id is None
        ):
            raise ValueError("Verification and apply jobs require a proposalId payload.")
        if self.job_type is JobType.APPLICATION_APPLY and self.payload.verification_id is None:
            raise ValueError("An apply job requires a verificationId payload.")
        if self.job_type is JobType.APPLICATION_UNDO and self.payload.application_id is None:
            raise ValueError("An undo job requires an applicationId payload.")
        return self


class JobCollection(ResourceModel):
    items: tuple[Job, ...]
    total: Annotated[int, Field(ge=0)]


class EnqueueVerificationJob(ResourceModel):
    job_type: Literal["proposal_verification"]
    proposal_id: UUID


class EnqueueApplyJob(ResourceModel):
    job_type: Literal["application_apply"]
    proposal_id: UUID
    verification_id: UUID


class EnqueueUndoJob(ResourceModel):
    job_type: Literal["application_undo"]
    application_id: UUID


class EnqueueBackupJob(ResourceModel):
    job_type: Literal["backup_create"]
    label: BoundedJobLabel | None = None


EnqueueJobRequest = Annotated[
    EnqueueVerificationJob | EnqueueApplyJob | EnqueueUndoJob | EnqueueBackupJob,
    Field(discriminator="job_type"),
]
