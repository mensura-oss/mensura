import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from mensura_core.application_service import ChangeApplicationService
from mensura_core.backup_service import BackupService
from mensura_core.event_publisher import EventPublisher
from mensura_core.exceptions import CoreError
from mensura_core.job_models import (
    JOB_LAST_ERROR_MAX_CHARS,
    Job,
    JobType,
)
from mensura_core.job_repositories import JobRepository
from mensura_core.job_service import make_job_event
from mensura_core.models import ensure_utc_timestamp
from mensura_core.service import utc_now
from mensura_core.undo_service import UndoService
from mensura_core.verification_service import ProposalVerificationService

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]

RESTART_RECOVERY_ERROR = (
    "Interrupted by a Core restart; the operation's outcome is unknown. "
    "Inspect the target artifact and re-enqueue if needed."
)
UNEXPECTED_ERROR = "An unexpected error occurred while executing this job."


class JobWorker:
    """Single in-process worker that drains the durable job queue.

    A job is pure orchestration: it invokes the same synchronous service method the
    equivalent HTTP endpoint calls, so every digest/guard/path/single-use safety check
    is preserved. Job success means the operation ran to completion and produced its
    artifact; the artifact's own status still records the domain outcome. Only pre-write
    refusals that raise a CoreError mark the job failed.
    """

    def __init__(
        self,
        job_repository: JobRepository,
        verification_service: ProposalVerificationService,
        application_service: ChangeApplicationService,
        undo_service: UndoService,
        backup_service: BackupService,
        *,
        worker_id: str = "core-worker-1",
        clock: Clock = utc_now,
        poll_interval: float = 0.5,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._repo = job_repository
        self._verification_service = verification_service
        self._application_service = application_service
        self._undo_service = undo_service
        self._backup_service = backup_service
        self._worker_id = worker_id
        self._clock = clock
        self._poll_interval = poll_interval
        self._event_publisher = event_publisher

    def recover_stale_jobs(self) -> int:
        """Reset jobs left running by an interrupted process to failed. Runs at startup."""
        recovered = self._repo.recover_running(
            now=ensure_utc_timestamp(self._clock()), last_error=RESTART_RECOVERY_ERROR
        )
        for job in recovered:
            self._publish(job)
        if recovered:
            logger.info(
                "Recovered %d interrupted running job(s) to failed on startup.", len(recovered)
            )
        return len(recovered)

    def process_next_job(self) -> Job | None:
        """Claim and execute at most one queued job. Returns the terminal job, or None."""
        claimed = self._repo.claim_next(
            worker_id=self._worker_id, now=ensure_utc_timestamp(self._clock())
        )
        if claimed is None:
            return None
        self._publish(claimed)  # running

        try:
            result_type, result_id = self._dispatch(claimed)
        except CoreError as error:
            return self._fail(claimed.id, str(error))
        except Exception:
            logger.exception("Unexpected error executing job %s", claimed.id)
            return self._fail(claimed.id, UNEXPECTED_ERROR)

        finished = self._repo.mark_succeeded(
            claimed.id,
            result_entity_type=result_type,
            result_entity_id=result_id,
            finished_at=ensure_utc_timestamp(self._clock()),
        )
        if finished is None:
            logger.warning("Job %s left running state before it could be marked done.", claimed.id)
            return None
        self._publish(finished)
        return finished

    async def run_forever(self) -> None:
        logger.info("Job worker %s started.", self._worker_id)
        try:
            while True:
                processed = await asyncio.to_thread(self.process_next_job)
                if processed is None:
                    await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            logger.info("Job worker %s stopped.", self._worker_id)
            raise

    def _dispatch(self, job: Job) -> tuple[str, UUID]:
        if job.job_type is JobType.PROPOSAL_VERIFICATION:
            verification = self._verification_service.verify(_require(job.payload.proposal_id))
            return "verification", verification.id
        if job.job_type is JobType.APPLICATION_APPLY:
            application = self._application_service.apply(
                _require(job.payload.proposal_id), _require(job.payload.verification_id)
            )
            return "application", application.id
        if job.job_type is JobType.APPLICATION_UNDO:
            undo = self._undo_service.undo(_require(job.payload.application_id))
            return "undo", undo.id
        backup = self._backup_service.create_backup(job.payload.label)
        return "backup", backup.id

    def _fail(self, job_id: UUID, last_error: str) -> Job | None:
        failed = self._repo.mark_failed(
            job_id,
            last_error=last_error[:JOB_LAST_ERROR_MAX_CHARS],
            finished_at=ensure_utc_timestamp(self._clock()),
        )
        if failed is None:
            logger.warning("Job %s left running state before it could be marked failed.", job_id)
            return None
        self._publish(failed)
        return failed

    def _publish(self, job: Job) -> None:
        if self._event_publisher is None:
            return
        self._event_publisher.publish(make_job_event(job))


def _require(value: UUID | None) -> UUID:
    if value is None:
        raise CoreError("Job payload is missing a required identifier.")
    return value
