from collections.abc import Callable, Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from mensura_core.job_models import Job, JobStatus, JobType
from mensura_core.persistence.models import JobRow


class SqlJobRepository:
    """SQLite-backed durable job queue. Claiming uses an atomic compare-and-set so that,
    even with multiple workers, exactly one claims a given queued job (SQLite serializes
    writes, so the losing UPDATE sees status != 'queued' and affects zero rows)."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def add(self, job: Job) -> None:
        with self._sf() as session:
            session.add(JobRow.from_domain(job))
            session.commit()

    def get(self, job_id: UUID) -> Job | None:
        with self._sf() as session:
            row = session.get(JobRow, job_id)
            return row.to_domain() if row is not None else None

    def list_all(
        self,
        *,
        workspace_id: UUID | None = None,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
    ) -> Sequence[Job]:
        with self._sf() as session:
            query = session.query(JobRow)
            if workspace_id is not None:
                query = query.filter(JobRow.workspace_id == workspace_id)
            if status is not None:
                query = query.filter(JobRow.status == status.value)
            if job_type is not None:
                query = query.filter(JobRow.job_type == job_type.value)
            rows = query.order_by(JobRow.created_at.desc(), JobRow.id.desc()).all()
            return tuple(row.to_domain() for row in rows)

    def claim_next(self, *, worker_id: str, now: datetime) -> Job | None:
        with self._sf() as session:
            job_id = session.execute(
                select(JobRow.id)
                .where(JobRow.status == JobStatus.QUEUED.value)
                .order_by(JobRow.created_at, JobRow.id)
                .limit(1)
            ).scalar_one_or_none()
            if job_id is None:
                return None
            result = session.execute(
                update(JobRow)
                .where(JobRow.id == job_id, JobRow.status == JobStatus.QUEUED.value)
                .values(
                    status=JobStatus.RUNNING.value,
                    started_at=now,
                    attempt_count=JobRow.attempt_count + 1,
                )
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                session.rollback()
                return None
            session.commit()
            claimed = session.get(JobRow, job_id)
            return claimed.to_domain() if claimed is not None else None

    def mark_succeeded(
        self,
        job_id: UUID,
        *,
        result_entity_type: str,
        result_entity_id: UUID,
        finished_at: datetime,
    ) -> Job | None:
        return self._finish(
            job_id,
            {
                "status": JobStatus.SUCCEEDED.value,
                "result_entity_type": result_entity_type,
                "result_entity_id": result_entity_id,
                "last_error": None,
                "finished_at": finished_at,
            },
        )

    def mark_failed(self, job_id: UUID, *, last_error: str, finished_at: datetime) -> Job | None:
        return self._finish(
            job_id,
            {
                "status": JobStatus.FAILED.value,
                "last_error": last_error,
                "finished_at": finished_at,
            },
        )

    def _finish(self, job_id: UUID, values: dict[str, object]) -> Job | None:
        with self._sf() as session:
            result = session.execute(
                update(JobRow)
                .where(JobRow.id == job_id, JobRow.status == JobStatus.RUNNING.value)
                .values(**values)
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                session.rollback()
                return None
            session.commit()
            row = session.get(JobRow, job_id)
            return row.to_domain() if row is not None else None

    def recover_running(self, *, now: datetime, last_error: str) -> Sequence[Job]:
        with self._sf() as session:
            ids = list(
                session.execute(
                    select(JobRow.id).where(JobRow.status == JobStatus.RUNNING.value)
                ).scalars()
            )
            if not ids:
                return ()
            session.execute(
                update(JobRow)
                .where(JobRow.status == JobStatus.RUNNING.value)
                .values(
                    status=JobStatus.FAILED.value,
                    last_error=last_error,
                    finished_at=now,
                )
                .execution_options(synchronize_session=False)
            )
            session.commit()
            rows = [session.get(JobRow, job_id) for job_id in ids]
            return tuple(row.to_domain() for row in rows if row is not None)

    def retry_job(self, *, original_job_id: UUID, retry_job: Job, now: datetime) -> Job | None:
        with self._sf() as session:
            original = session.get(JobRow, original_job_id)
            if original is None:
                return None
            if original.status != JobStatus.FAILED.value:
                return None
            if not original.retry_eligible:
                return None

            retry_row = JobRow.from_domain(retry_job)
            session.add(retry_row)

            session.execute(
                update(JobRow)
                .where(JobRow.id == original_job_id)
                .values(
                    retry_eligible=False,
                    retry_count=JobRow.retry_count + 1,
                )
                .execution_options(synchronize_session=False)
            )
            session.commit()
            return retry_job

    def delete(self, job_id: UUID) -> bool:
        with self._sf() as session:
            row = session.get(JobRow, job_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
