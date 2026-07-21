from collections.abc import Sequence
from datetime import datetime
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.job_models import Job, JobStatus, JobType


def _with(job: Job, **updates: object) -> Job:
    """Re-validate a lifecycle transition rather than bypassing model invariants."""
    return Job.model_validate({**job.model_dump(by_alias=False), **updates})


class JobRepository(Protocol):
    def add(self, job: Job) -> None: ...

    def get(self, job_id: UUID) -> Job | None: ...

    def list_all(
        self,
        *,
        workspace_id: UUID | None = None,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
    ) -> Sequence[Job]: ...

    def claim_next(self, *, worker_id: str, now: datetime) -> Job | None:
        """Atomically move the oldest queued job to running. Only one worker wins."""
        ...

    def mark_succeeded(
        self,
        job_id: UUID,
        *,
        result_entity_type: str,
        result_entity_id: UUID,
        finished_at: datetime,
    ) -> Job | None: ...

    def mark_failed(
        self, job_id: UUID, *, last_error: str, finished_at: datetime
    ) -> Job | None: ...

    def recover_running(self, *, now: datetime, last_error: str) -> Sequence[Job]:
        """Transition interrupted running jobs to failed on startup. Returns recovered jobs."""
        ...


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[UUID, Job] = {}
        self._lock = RLock()

    def add(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job

    def get(self, job_id: UUID) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_all(
        self,
        *,
        workspace_id: UUID | None = None,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
    ) -> Sequence[Job]:
        with self._lock:
            jobs = [
                job
                for job in self._jobs.values()
                if (workspace_id is None or job.workspace_id == workspace_id)
                and (status is None or job.status is status)
                and (job_type is None or job.job_type is job_type)
            ]
        return tuple(sorted(jobs, key=lambda j: (j.created_at, str(j.id)), reverse=True))

    def claim_next(self, *, worker_id: str, now: datetime) -> Job | None:
        with self._lock:
            queued = [job for job in self._jobs.values() if job.status is JobStatus.QUEUED]
            if not queued:
                return None
            oldest = min(queued, key=lambda j: (j.created_at, str(j.id)))
            claimed = _with(
                oldest,
                status=JobStatus.RUNNING,
                started_at=now,
                attempt_count=oldest.attempt_count + 1,
            )
            self._jobs[claimed.id] = claimed
            return claimed

    def mark_succeeded(
        self,
        job_id: UUID,
        *,
        result_entity_type: str,
        result_entity_id: UUID,
        finished_at: datetime,
    ) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status is not JobStatus.RUNNING:
                return None
            updated = _with(
                job,
                status=JobStatus.SUCCEEDED,
                result_entity_type=result_entity_type,
                result_entity_id=result_entity_id,
                last_error=None,
                finished_at=finished_at,
            )
            self._jobs[updated.id] = updated
            return updated

    def mark_failed(self, job_id: UUID, *, last_error: str, finished_at: datetime) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status is not JobStatus.RUNNING:
                return None
            updated = _with(
                job,
                status=JobStatus.FAILED,
                last_error=last_error,
                finished_at=finished_at,
            )
            self._jobs[updated.id] = updated
            return updated

    def recover_running(self, *, now: datetime, last_error: str) -> Sequence[Job]:
        with self._lock:
            recovered: list[Job] = []
            for job in list(self._jobs.values()):
                if job.status is JobStatus.RUNNING:
                    started_at = job.started_at
                    updated = _with(
                        job,
                        status=JobStatus.FAILED,
                        last_error=last_error,
                        finished_at=max(now, started_at) if started_at is not None else now,
                    )
                    self._jobs[updated.id] = updated
                    recovered.append(updated)
            return tuple(recovered)
