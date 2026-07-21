"""Deterministic unit tests for the durable job queue: claim atomicity, persisted
state transitions, restart recovery, SSE publication, and refusal/error propagation.

These use stub services (the worker is duck-typed) so they exercise the queue and
worker mechanics without a Git repository or provider. Real end-to-end integration
with verify/apply/undo/backup lives in test_jobs_api.py."""

import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from mensura_core.event_publisher import MensuraEvent
from mensura_core.exceptions import (
    ApplicationLiveDriftError,
    ChangeProposalNotFoundError,
    JobNotFoundError,
    JobRetryNotEligibleError,
)
from mensura_core.job_models import (
    EnqueueBackupJob,
    EnqueueVerificationJob,
    Job,
    JobPayload,
    JobStatus,
    JobTargetType,
    JobType,
)
from mensura_core.job_repositories import InMemoryJobRepository
from mensura_core.job_service import JobService
from mensura_core.job_worker import RESTART_RECOVERY_ERROR, UNEXPECTED_ERROR, JobWorker
from mensura_core.persistence import SqlJobRepository
from mensura_core.persistence.database import (
    create_persistence_engine,
    create_session_factory,
    run_migrations,
)


def _now() -> datetime:
    return datetime.now(UTC)


class RecordingPublisher:
    def __init__(self) -> None:
        self.events: list[MensuraEvent] = []

    def publish(self, event: MensuraEvent) -> None:
        self.events.append(event)


class StubServices:
    """One object standing in for all four downstream services (duck-typed)."""

    def __init__(self, *, result_id: UUID | None = None, error: Exception | None = None) -> None:
        self.result_id = result_id or uuid4()
        self.error = error
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def _do(self, name: str, *args: object) -> SimpleNamespace:
        self.calls.append((name, args))
        if self.error is not None:
            raise self.error
        return SimpleNamespace(id=self.result_id)

    def verify(self, proposal_id: UUID) -> SimpleNamespace:
        return self._do("verify", proposal_id)

    def apply(self, proposal_id: UUID, verification_id: UUID) -> SimpleNamespace:
        return self._do("apply", proposal_id, verification_id)

    def undo(self, application_id: UUID) -> SimpleNamespace:
        return self._do("undo", application_id)

    def create_backup(self, label: str | None = None) -> SimpleNamespace:
        return self._do("create_backup", label)


class FakeEntityRepo:
    """Minimal proposal/application repo: returns an object with workspace_id if present."""

    def __init__(self, workspace_id: UUID | None) -> None:
        self._workspace_id = workspace_id

    def get(self, _entity_id: UUID) -> SimpleNamespace | None:
        if self._workspace_id is None:
            return None
        return SimpleNamespace(workspace_id=self._workspace_id)


def _make_worker(
    repo: InMemoryJobRepository | SqlJobRepository,
    stub: StubServices,
    publisher: RecordingPublisher | None = None,
) -> JobWorker:
    return JobWorker(repo, stub, stub, stub, stub, event_publisher=publisher)


def _make_service(
    repo: InMemoryJobRepository | SqlJobRepository,
    *,
    workspace_id: UUID | None,
    publisher: RecordingPublisher | None = None,
) -> JobService:
    return JobService(
        repo,
        FakeEntityRepo(workspace_id),
        FakeEntityRepo(workspace_id),
        event_publisher=publisher,
    )


def _queued_job(job_type: JobType, payload: JobPayload, target_id: UUID | None) -> Job:
    target_type = (
        JobTargetType.DATABASE
        if job_type is JobType.BACKUP_CREATE
        else (
            JobTargetType.APPLICATION
            if job_type is JobType.APPLICATION_UNDO
            else JobTargetType.CHANGE_PROPOSAL
        )
    )
    return Job(
        id=uuid4(),
        job_type=job_type,
        target_entity_type=target_type,
        target_entity_id=target_id,
        workspace_id=None,
        status=JobStatus.QUEUED,
        attempt_count=0,
        payload=payload,
        result_entity_type=None,
        result_entity_id=None,
        last_error=None,
        created_at=_now(),
        started_at=None,
        finished_at=None,
    )


# --------------------------------------------------------------------------- enqueue


def test_enqueue_verification_job_is_queued_and_publishes() -> None:
    repo = InMemoryJobRepository()
    publisher = RecordingPublisher()
    workspace_id = uuid4()
    proposal_id = uuid4()
    service = _make_service(repo, workspace_id=workspace_id, publisher=publisher)

    job = service.enqueue(
        EnqueueVerificationJob(job_type="proposal_verification", proposal_id=proposal_id)
    )

    assert job.status is JobStatus.QUEUED
    assert job.job_type is JobType.PROPOSAL_VERIFICATION
    assert job.target_entity_type is JobTargetType.CHANGE_PROPOSAL
    assert job.target_entity_id == proposal_id
    assert job.workspace_id == workspace_id
    assert job.payload.proposal_id == proposal_id
    assert job.attempt_count == 0
    assert job.started_at is None and job.finished_at is None
    assert repo.get(job.id) == job
    assert len(publisher.events) == 1
    assert publisher.events[0].event_type == "job.status.changed"
    assert publisher.events[0].status == "queued"


def test_enqueue_unknown_proposal_raises() -> None:
    repo = InMemoryJobRepository()
    service = _make_service(repo, workspace_id=None)

    with pytest.raises(ChangeProposalNotFoundError):
        service.enqueue(
            EnqueueVerificationJob(job_type="proposal_verification", proposal_id=uuid4())
        )


def test_enqueue_backup_job_has_no_target_entity() -> None:
    repo = InMemoryJobRepository()
    service = _make_service(repo, workspace_id=None)

    job = service.enqueue(EnqueueBackupJob(job_type="backup_create", label="nightly"))

    assert job.job_type is JobType.BACKUP_CREATE
    assert job.target_entity_type is JobTargetType.DATABASE
    assert job.target_entity_id is None
    assert job.workspace_id is None
    assert job.payload.label == "nightly"


def test_get_unknown_job_raises() -> None:
    service = _make_service(InMemoryJobRepository(), workspace_id=None)
    with pytest.raises(JobNotFoundError):
        service.get(uuid4())


# ------------------------------------------------------------------- worker execution


def test_worker_claims_and_executes_a_verification_job() -> None:
    repo = InMemoryJobRepository()
    result_id = uuid4()
    stub = StubServices(result_id=result_id)
    proposal_id = uuid4()
    service = _make_service(repo, workspace_id=uuid4())
    worker = _make_worker(repo, stub)

    queued = service.enqueue(
        EnqueueVerificationJob(job_type="proposal_verification", proposal_id=proposal_id)
    )
    finished = worker.process_next_job()

    assert finished is not None
    assert finished.id == queued.id
    assert finished.status is JobStatus.SUCCEEDED
    assert finished.result_entity_type == "verification"
    assert finished.result_entity_id == result_id
    assert finished.attempt_count == 1
    assert finished.last_error is None
    assert stub.calls == [("verify", (proposal_id,))]
    # Persisted, and the queue is now empty.
    assert repo.get(queued.id).status is JobStatus.SUCCEEDED
    assert worker.process_next_job() is None


def test_worker_dispatches_each_job_type_to_the_right_service() -> None:
    repo = InMemoryJobRepository()
    stub = StubServices()
    worker = _make_worker(repo, stub)
    proposal_id, verification_id, application_id = uuid4(), uuid4(), uuid4()

    repo.add(
        _queued_job(
            JobType.APPLICATION_APPLY,
            JobPayload(proposal_id=proposal_id, verification_id=verification_id),
            proposal_id,
        )
    )
    worker.process_next_job()
    repo.add(
        _queued_job(
            JobType.APPLICATION_UNDO, JobPayload(application_id=application_id), application_id
        )
    )
    worker.process_next_job()
    repo.add(_queued_job(JobType.BACKUP_CREATE, JobPayload(label="x"), None))
    worker.process_next_job()

    names = [name for name, _ in stub.calls]
    assert names == ["apply", "undo", "create_backup"]
    assert stub.calls[0][1] == (proposal_id, verification_id)


def test_worker_publishes_running_then_terminal_events() -> None:
    repo = InMemoryJobRepository()
    publisher = RecordingPublisher()
    service = _make_service(repo, workspace_id=uuid4(), publisher=publisher)
    worker = _make_worker(repo, StubServices(), publisher)

    service.enqueue(EnqueueVerificationJob(job_type="proposal_verification", proposal_id=uuid4()))
    worker.process_next_job()

    statuses = [e.status for e in publisher.events]
    assert statuses == ["queued", "running", "succeeded"]
    assert all(e.event_type == "job.status.changed" for e in publisher.events)


def test_worker_marks_failed_on_core_error_refusal() -> None:
    repo = InMemoryJobRepository()
    publisher = RecordingPublisher()
    stub = StubServices(error=ApplicationLiveDriftError("src/example.py"))
    worker = _make_worker(repo, stub, publisher)
    proposal_id, verification_id = uuid4(), uuid4()
    repo.add(
        _queued_job(
            JobType.APPLICATION_APPLY,
            JobPayload(proposal_id=proposal_id, verification_id=verification_id),
            proposal_id,
        )
    )

    finished = worker.process_next_job()

    assert finished is not None
    assert finished.status is JobStatus.FAILED
    assert finished.result_entity_id is None
    assert "drifted" in finished.last_error
    assert finished.attempt_count == 1
    assert publisher.events[-1].status == "failed"


def test_worker_marks_failed_on_unexpected_error_without_leaking_details() -> None:
    repo = InMemoryJobRepository()
    stub = StubServices(error=RuntimeError("boom secret internals"))
    worker = _make_worker(repo, stub)
    repo.add(_queued_job(JobType.BACKUP_CREATE, JobPayload(label=None), None))

    finished = worker.process_next_job()

    assert finished is not None
    assert finished.status is JobStatus.FAILED
    assert finished.last_error == UNEXPECTED_ERROR
    assert "boom" not in finished.last_error


def test_worker_returns_none_when_queue_is_empty() -> None:
    worker = _make_worker(InMemoryJobRepository(), StubServices())
    assert worker.process_next_job() is None


# ------------------------------------------------------------ claim atomicity & recovery


@pytest.fixture(params=["memory", "sql"])
def repo(request: pytest.FixtureRequest):  # type: ignore[no-untyped-def]
    if request.param == "memory":
        yield InMemoryJobRepository()
        return
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="mensura_jobs_")
    os.close(fd)
    db_url = f"sqlite:///{db_path}"
    run_migrations(db_url)
    engine = create_persistence_engine(db_url)
    try:
        yield SqlJobRepository(create_session_factory(engine))
    finally:
        engine.dispose()
        Path(db_path).unlink(missing_ok=True)


def test_claim_is_single_use_compare_and_set(repo) -> None:  # type: ignore[no-untyped-def]
    job = _queued_job(JobType.BACKUP_CREATE, JobPayload(label="a"), None)
    repo.add(job)

    claimed = repo.claim_next(worker_id="w1", now=_now())
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status is JobStatus.RUNNING
    assert claimed.attempt_count == 1
    # Re-claiming the same running job is impossible; the queue is now empty.
    assert repo.claim_next(worker_id="w2", now=_now()) is None

    done = repo.mark_succeeded(
        job.id, result_entity_type="backup", result_entity_id=uuid4(), finished_at=_now()
    )
    assert done is not None and done.status is JobStatus.SUCCEEDED
    # A second terminal transition on a non-running job is a no-op.
    assert repo.mark_failed(job.id, last_error="late", finished_at=_now()) is None


def test_claim_returns_oldest_first(repo) -> None:  # type: ignore[no-untyped-def]
    first = _queued_job(JobType.BACKUP_CREATE, JobPayload(label="first"), None)
    repo.add(first)
    second = _queued_job(JobType.BACKUP_CREATE, JobPayload(label="second"), None)
    # Ensure a strictly later created_at so ordering is deterministic.
    second = second.model_copy(update={"created_at": first.created_at + timedelta(seconds=1)})
    repo.add(second)

    claimed = repo.claim_next(worker_id="w1", now=_now())
    assert claimed is not None
    assert claimed.payload.label == "first"


def test_recover_running_marks_interrupted_jobs_failed(repo) -> None:  # type: ignore[no-untyped-def]
    interrupted = _queued_job(JobType.BACKUP_CREATE, JobPayload(label="running"), None)
    repo.add(interrupted)
    still_queued = _queued_job(JobType.BACKUP_CREATE, JobPayload(label="queued"), None)
    repo.add(still_queued)

    claimed = repo.claim_next(worker_id="w1", now=_now())
    assert claimed is not None and claimed.status is JobStatus.RUNNING

    recovered = repo.recover_running(now=_now(), last_error=RESTART_RECOVERY_ERROR)

    assert len(recovered) == 1
    assert recovered[0].id == interrupted.id
    assert repo.get(interrupted.id).status is JobStatus.FAILED
    assert repo.get(interrupted.id).last_error == RESTART_RECOVERY_ERROR
    # A queued job is untouched and can still be claimed after recovery.
    assert repo.get(still_queued.id).status is JobStatus.QUEUED
    next_claim = repo.claim_next(worker_id="w1", now=_now())
    assert next_claim is not None and next_claim.id == still_queued.id


def test_worker_recover_stale_jobs_publishes_failed_event(repo) -> None:  # type: ignore[no-untyped-def]
    publisher = RecordingPublisher()
    worker = _make_worker(repo, StubServices(), publisher)
    job = _queued_job(JobType.BACKUP_CREATE, JobPayload(label="running"), None)
    repo.add(job)
    repo.claim_next(worker_id="w1", now=_now())

    count = worker.recover_stale_jobs()

    assert count == 1
    assert repo.get(job.id).status is JobStatus.FAILED
    assert publisher.events[-1].status == "failed"


def test_sql_jobs_persist_across_restart() -> None:
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="mensura_jobs_restart_")
    os.close(fd)
    db_url = f"sqlite:///{db_path}"
    try:
        run_migrations(db_url)
        engine1 = create_persistence_engine(db_url)
        repo1 = SqlJobRepository(create_session_factory(engine1))
        # The interrupted job is older, so claim_next (oldest-first) picks it to run.
        running = _queued_job(JobType.BACKUP_CREATE, JobPayload(label="interrupted"), None)
        running = running.model_copy(update={"created_at": _now() - timedelta(seconds=1)})
        repo1.add(running)
        queued = _queued_job(JobType.BACKUP_CREATE, JobPayload(label="survivor"), None)
        repo1.add(queued)
        claimed = repo1.claim_next(worker_id="w1", now=_now())
        assert claimed is not None and claimed.id == running.id
        engine1.dispose()  # simulate a crash mid-run

        # Restart: fresh engine/session on the same database file.
        engine2 = create_persistence_engine(db_url)
        repo2 = SqlJobRepository(create_session_factory(engine2))
        assert repo2.get(queued.id).status is JobStatus.QUEUED
        assert repo2.get(claimed.id).status is JobStatus.RUNNING

        recovered = repo2.recover_running(now=_now(), last_error=RESTART_RECOVERY_ERROR)
        assert [j.id for j in recovered] == [claimed.id]
        assert repo2.get(claimed.id).status is JobStatus.FAILED
        # The queued job still drains normally after recovery.
        drained = repo2.claim_next(worker_id="w1", now=_now())
        assert drained is not None and drained.id == queued.id
        engine2.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


# -------------------------------------------------------------------- retry


def test_retry_creates_new_linked_job_and_exhausts_original() -> None:
    repo = InMemoryJobRepository()
    publisher = RecordingPublisher()
    workspace_id = uuid4()
    proposal_id = uuid4()
    service = _make_service(repo, workspace_id=workspace_id, publisher=publisher)

    original = service.enqueue(
        EnqueueVerificationJob(job_type="proposal_verification", proposal_id=proposal_id)
    )
    # Simulate the worker: claim → fail
    claimed = repo.claim_next(worker_id="w1", now=_now())
    assert claimed is not None
    failed = repo.mark_failed(claimed.id, last_error="Something broke", finished_at=_now())
    assert failed is not None and failed.status is JobStatus.FAILED

    # Retry it
    retry = service.retry(original.id)
    assert retry.id != original.id
    assert retry.status is JobStatus.QUEUED
    assert retry.job_type is JobType.PROPOSAL_VERIFICATION
    assert retry.retry_of_job_id == original.id
    assert retry.root_job_id == original.id
    assert retry.retry_eligible is True
    assert retry.retry_count == 0
    assert retry.attempt_count == 0
    assert retry.payload.proposal_id == proposal_id

    # Original is exhausted
    orig_after = repo.get(original.id)
    assert orig_after is not None
    assert orig_after.retry_eligible is False
    assert orig_after.retry_count == 1

    # Events published for both
    statuses = [(e.entity_id, e.status) for e in publisher.events]
    assert (str(original.id), "queued") in statuses
    assert (str(retry.id), "queued") in statuses


def test_retry_refuses_non_failed_job() -> None:
    repo = InMemoryJobRepository()
    service = _make_service(repo, workspace_id=uuid4())
    job = service.enqueue(
        EnqueueVerificationJob(job_type="proposal_verification", proposal_id=uuid4())
    )
    with pytest.raises(JobRetryNotEligibleError, match="Only failed jobs"):
        service.retry(job.id)


def test_retry_refuses_already_exhausted_job() -> None:
    repo = InMemoryJobRepository()
    publisher = RecordingPublisher()
    service = _make_service(repo, workspace_id=uuid4(), publisher=publisher)

    original = service.enqueue(
        EnqueueVerificationJob(job_type="proposal_verification", proposal_id=uuid4())
    )
    repo.claim_next(worker_id="w1", now=_now())
    repo.mark_failed(original.id, last_error="x", finished_at=_now())
    service.retry(original.id)

    with pytest.raises(JobRetryNotEligibleError, match="already been retried"):
        service.retry(original.id)


def test_retry_refuses_unsupported_job_type() -> None:
    repo = InMemoryJobRepository()
    publisher = RecordingPublisher()
    service = _make_service(repo, workspace_id=uuid4(), publisher=publisher)

    backup = service.enqueue(EnqueueBackupJob(job_type="backup_create", label="nightly"))
    repo.claim_next(worker_id="w1", now=_now())
    repo.mark_failed(backup.id, last_error="boom", finished_at=_now())

    with pytest.raises(JobRetryNotEligibleError, match="does not support retry"):
        service.retry(backup.id)


def test_retry_child_can_be_retried_itself() -> None:
    repo = InMemoryJobRepository()
    publisher = RecordingPublisher()
    service = _make_service(repo, workspace_id=uuid4(), publisher=publisher)

    original = service.enqueue(
        EnqueueVerificationJob(job_type="proposal_verification", proposal_id=uuid4())
    )
    repo.claim_next(worker_id="w1", now=_now())
    repo.mark_failed(original.id, last_error="first", finished_at=_now())

    retry1 = service.retry(original.id)
    repo.claim_next(worker_id="w1", now=_now())
    repo.mark_failed(retry1.id, last_error="second", finished_at=_now())

    # The retry child itself is retry-eligible
    assert repo.get(retry1.id).retry_eligible is True

    retry2 = service.retry(retry1.id)
    assert retry2.retry_of_job_id == retry1.id
    assert retry2.root_job_id == original.id
    assert retry2.status is JobStatus.QUEUED


def test_retry_preserves_workspace_and_target_from_original() -> None:
    repo = InMemoryJobRepository()
    workspace_id = uuid4()
    proposal_id = uuid4()
    service = _make_service(repo, workspace_id=workspace_id)

    original = service.enqueue(
        EnqueueVerificationJob(job_type="proposal_verification", proposal_id=proposal_id)
    )
    repo.claim_next(worker_id="w1", now=_now())
    repo.mark_failed(original.id, last_error="x", finished_at=_now())

    retry = service.retry(original.id)

    assert retry.workspace_id == workspace_id
    assert retry.target_entity_id == proposal_id
    assert retry.target_entity_type is JobTargetType.CHANGE_PROPOSAL


def test_retry_via_sql_repository(repo) -> None:  # type: ignore[no-untyped-def]
    publisher = RecordingPublisher()
    workspace_id = uuid4()
    proposal_id = uuid4()
    service = _make_service(repo, workspace_id=workspace_id, publisher=publisher)

    original = service.enqueue(
        EnqueueVerificationJob(job_type="proposal_verification", proposal_id=proposal_id)
    )
    repo.claim_next(worker_id="w1", now=_now())
    repo.mark_failed(original.id, last_error="drifted", finished_at=_now())

    retry = service.retry(original.id)
    assert retry.status is JobStatus.QUEUED
    assert retry.retry_of_job_id == original.id

    orig_reloaded = repo.get(original.id)
    assert orig_reloaded is not None
    assert orig_reloaded.retry_eligible is False
    assert orig_reloaded.retry_count == 1

    # The retry can be claimed and executed
    claimed = repo.claim_next(worker_id="w1", now=_now())
    assert claimed is not None and claimed.id == retry.id
    result_id = uuid4()
    done = repo.mark_succeeded(
        retry.id, result_entity_type="verification", result_entity_id=result_id, finished_at=_now()
    )
    assert done is not None and done.status is JobStatus.SUCCEEDED
    assert done.retry_of_job_id == original.id
