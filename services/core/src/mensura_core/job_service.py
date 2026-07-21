from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from mensura_core.application_repositories import ApplicationRepository
from mensura_core.change_proposal_repositories import ChangeProposalRepository
from mensura_core.event_publisher import EventPublisher, MensuraEvent
from mensura_core.exceptions import (
    ApplicationNotFoundError,
    ChangeProposalNotFoundError,
    JobNotFoundError,
)
from mensura_core.job_models import (
    EnqueueApplyJob,
    EnqueueBackupJob,
    EnqueueUndoJob,
    EnqueueVerificationJob,
    Job,
    JobCollection,
    JobPayload,
    JobStatus,
    JobTargetType,
    JobType,
)
from mensura_core.job_repositories import JobRepository
from mensura_core.models import ensure_utc_timestamp
from mensura_core.service import utc_now

IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]

EnqueueRequest = EnqueueVerificationJob | EnqueueApplyJob | EnqueueUndoJob | EnqueueBackupJob


def make_job_event(job: Job) -> MensuraEvent:
    summary = f"Job {job.job_type.value} {job.status.value}."
    if job.status is JobStatus.FAILED and job.last_error:
        summary = f"Job {job.job_type.value} failed: {job.last_error}"
    return MensuraEvent(
        event_type="job.status.changed",
        workspace_id=job.workspace_id,
        entity_type="job",
        entity_id=job.id,
        status=job.status.value,
        summary=summary,
    )


class JobService:
    """Enqueue and inspect durable background jobs. Execution belongs to the worker."""

    def __init__(
        self,
        job_repository: JobRepository,
        proposal_repository: ChangeProposalRepository,
        application_repository: ApplicationRepository,
        *,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._repo = job_repository
        self._proposal_repository = proposal_repository
        self._application_repository = application_repository
        self._id_factory = id_factory
        self._clock = clock
        self._event_publisher = event_publisher

    def enqueue(self, request: EnqueueRequest) -> Job:
        if isinstance(request, EnqueueVerificationJob):
            workspace_id = self._require_proposal_workspace(request.proposal_id)
            job = self._new_job(
                JobType.PROPOSAL_VERIFICATION,
                JobTargetType.CHANGE_PROPOSAL,
                request.proposal_id,
                workspace_id,
                JobPayload(proposal_id=request.proposal_id),
            )
        elif isinstance(request, EnqueueApplyJob):
            workspace_id = self._require_proposal_workspace(request.proposal_id)
            job = self._new_job(
                JobType.APPLICATION_APPLY,
                JobTargetType.CHANGE_PROPOSAL,
                request.proposal_id,
                workspace_id,
                JobPayload(
                    proposal_id=request.proposal_id,
                    verification_id=request.verification_id,
                ),
            )
        elif isinstance(request, EnqueueUndoJob):
            workspace_id = self._require_application_workspace(request.application_id)
            job = self._new_job(
                JobType.APPLICATION_UNDO,
                JobTargetType.APPLICATION,
                request.application_id,
                workspace_id,
                JobPayload(application_id=request.application_id),
            )
        else:
            job = self._new_job(
                JobType.BACKUP_CREATE,
                JobTargetType.DATABASE,
                None,
                None,
                JobPayload(label=request.label),
            )

        self._repo.add(job)
        self._publish(job)
        return job

    def get(self, job_id: UUID) -> Job:
        job = self._repo.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job

    def list_jobs(
        self,
        *,
        workspace_id: UUID | None = None,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
    ) -> JobCollection:
        items = tuple(
            self._repo.list_all(workspace_id=workspace_id, status=status, job_type=job_type)
        )
        return JobCollection(items=items, total=len(items))

    def _new_job(
        self,
        job_type: JobType,
        target_type: JobTargetType,
        target_id: UUID | None,
        workspace_id: UUID | None,
        payload: JobPayload,
    ) -> Job:
        return Job(
            id=self._id_factory(),
            job_type=job_type,
            target_entity_type=target_type,
            target_entity_id=target_id,
            workspace_id=workspace_id,
            status=JobStatus.QUEUED,
            attempt_count=0,
            payload=payload,
            result_entity_type=None,
            result_entity_id=None,
            last_error=None,
            created_at=ensure_utc_timestamp(self._clock()),
            started_at=None,
            finished_at=None,
        )

    def _require_proposal_workspace(self, proposal_id: UUID) -> UUID:
        proposal = self._proposal_repository.get(proposal_id)
        if proposal is None:
            raise ChangeProposalNotFoundError(proposal_id)
        return proposal.workspace_id

    def _require_application_workspace(self, application_id: UUID) -> UUID:
        application = self._application_repository.get(application_id)
        if application is None:
            raise ApplicationNotFoundError(application_id)
        return application.workspace_id

    def _publish(self, job: Job) -> None:
        if self._event_publisher is None:
            return
        self._event_publisher.publish(make_job_event(job))
