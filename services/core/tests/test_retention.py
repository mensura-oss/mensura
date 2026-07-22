"""Unit tests for the retention policy and backup/job pruning."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from mensura_core.application_repositories import InMemoryApplicationRepository
from mensura_core.backup_models import BackupArtifact, BackupStatus
from mensura_core.backup_repositories import InMemoryBackupRepository
from mensura_core.backup_service import BackupService
from mensura_core.change_proposal_repositories import InMemoryChangeProposalRepository
from mensura_core.job_models import Job, JobPayload, JobStatus, JobTargetType, JobType
from mensura_core.job_repositories import InMemoryJobRepository
from mensura_core.job_service import JobService
from mensura_core.retention import (
    RetentionPolicy,
    backup_retention_from_env,
    job_retention_from_env,
)

BASE = datetime(2026, 1, 1, tzinfo=UTC)


# --------------------------------------------------------------- RetentionPolicy logic


def _days(offsets: list[int]) -> list[datetime]:
    """Timestamps at the given day offsets from BASE (used as the items themselves)."""
    return [BASE + timedelta(days=offset) for offset in offsets]


def test_count_only_keeps_newest_n() -> None:
    items = _days([0, 1, 2, 3, 4])  # oldest..newest
    policy = RetentionPolicy(max_count=2, max_age_days=0)
    kept, pruned = policy.partition(items, now=BASE + timedelta(days=100), timestamp=lambda d: d)
    assert set(kept) == set(_days([3, 4]))
    assert set(pruned) == set(_days([0, 1, 2]))


def test_age_only_keeps_recent() -> None:
    items = _days([0, 50, 90])
    policy = RetentionPolicy(max_count=0, max_age_days=30)
    now = BASE + timedelta(days=100)  # cutoff = day 70
    kept, pruned = policy.partition(items, now=now, timestamp=lambda d: d)
    assert set(kept) == set(_days([90]))
    assert set(pruned) == set(_days([0, 50]))


def test_union_keeps_when_either_condition_holds() -> None:
    items = _days([0, 50, 90, 95])
    # Keep newest 1 OR newer than 30 days (cutoff day 70).
    policy = RetentionPolicy(max_count=1, max_age_days=30)
    now = BASE + timedelta(days=100)
    kept, pruned = policy.partition(items, now=now, timestamp=lambda d: d)
    # day 95 (count+age), day 90 (age) kept; day 0 and 50 pruned (fail both).
    assert set(kept) == set(_days([90, 95]))
    assert set(pruned) == set(_days([0, 50]))


def test_both_zero_disables_pruning() -> None:
    items = _days([0, 1, 2])
    policy = RetentionPolicy(max_count=0, max_age_days=0)
    assert not policy.enabled
    kept, pruned = policy.partition(items, now=BASE + timedelta(days=999), timestamp=lambda d: d)
    assert set(kept) == set(items)
    assert pruned == []


def test_keep_at_least_protects_newest_even_when_ancient() -> None:
    items = _days([0, 1])  # both far older than the age cutoff
    # Age-only policy that would prune everything, but keep_at_least=1 saves the newest.
    policy = RetentionPolicy(max_count=0, max_age_days=1, keep_at_least=1)
    now = BASE + timedelta(days=999)
    kept, pruned = policy.partition(items, now=now, timestamp=lambda d: d)
    assert kept == _days([1])  # newest survives
    assert pruned == _days([0])


def test_partition_is_order_independent() -> None:
    ordered = _days([0, 1, 2, 3])
    shuffled = [ordered[2], ordered[0], ordered[3], ordered[1]]
    policy = RetentionPolicy(max_count=2, max_age_days=0)
    kept, pruned = policy.partition(shuffled, now=BASE + timedelta(days=100), timestamp=lambda d: d)
    assert set(kept) == set(_days([2, 3]))
    assert set(pruned) == set(_days([0, 1]))


def test_from_env_defaults_and_overrides() -> None:
    backup_default = backup_retention_from_env(env={})
    assert backup_default.max_count == 10
    assert backup_default.max_age_days == 30
    assert backup_default.keep_at_least == 1

    job_default = job_retention_from_env(env={})
    assert job_default.max_count == 200
    assert job_default.max_age_days == 30
    assert job_default.keep_at_least == 0

    overridden = backup_retention_from_env(
        env={"MENSURA_BACKUP_RETENTION_COUNT": "3", "MENSURA_BACKUP_RETENTION_DAYS": "7"}
    )
    assert (overridden.max_count, overridden.max_age_days) == (3, 7)


def test_from_env_invalid_and_negative_are_normalized() -> None:
    invalid = backup_retention_from_env(env={"MENSURA_BACKUP_RETENTION_COUNT": "not-a-number"})
    assert invalid.max_count == 10  # falls back to default
    negative = backup_retention_from_env(
        env={"MENSURA_BACKUP_RETENTION_COUNT": "-5", "MENSURA_BACKUP_RETENTION_DAYS": "-1"}
    )
    assert (negative.max_count, negative.max_age_days) == (0, 0)  # clamped, so disabled


# --------------------------------------------------------------- backup pruning


def _backup(created_at: datetime, storage_path: str) -> BackupArtifact:
    return BackupArtifact(
        id=uuid4(),
        created_at=created_at,
        db_version="005",
        file_size_bytes=10,
        sha256_hex="ab" * 32,
        storage_path=storage_path,
        status=BackupStatus.COMPLETED,
    )


def _backup_service(
    backup_dir: Path, policy: RetentionPolicy | None
) -> tuple[BackupService, InMemoryBackupRepository]:
    repo = InMemoryBackupRepository()
    service = BackupService(
        backup_repository=repo,
        backup_dir=backup_dir,
        engine=None,
        retention_policy=policy,
    )
    return service, repo


def _seed_backup(repo: InMemoryBackupRepository, backup_dir: Path, backup: BackupArtifact) -> Path:
    repo.add(backup)
    file_path = backup_dir / backup.storage_path
    file_path.write_bytes(b"snapshot")
    return file_path


def test_prune_backups_deletes_files_and_rows_beyond_count(tmp_path: Path) -> None:
    policy = RetentionPolicy(max_count=2, max_age_days=0, keep_at_least=1)
    service, repo = _backup_service(tmp_path, policy)
    files = {}
    for offset in range(4):  # 4 backups, keep newest 2
        backup = _backup(BASE + timedelta(days=offset), f"backup-{offset}.db")
        files[offset] = _seed_backup(repo, tmp_path, backup)

    result = service.prune()

    assert (result.inspected, result.deleted, result.kept, result.failed) == (4, 2, 2, 0)
    # Oldest two files + rows are gone; newest two remain.
    assert not files[0].exists() and not files[1].exists()
    assert files[2].exists() and files[3].exists()
    assert len(repo.list_all()) == 2


def test_prune_never_deletes_the_only_backup(tmp_path: Path) -> None:
    # An aggressive age-only policy that would otherwise prune an ancient sole backup.
    policy = RetentionPolicy(max_count=0, max_age_days=1, keep_at_least=1)
    service, repo = _backup_service(tmp_path, policy)
    ancient = _backup(datetime.now(UTC) - timedelta(days=365), "only.db")
    file_path = _seed_backup(repo, tmp_path, ancient)

    result = service.prune()

    assert result.deleted == 0
    assert file_path.exists()
    assert len(repo.list_all()) == 1


def test_prune_backups_by_age(tmp_path: Path) -> None:
    policy = RetentionPolicy(max_count=0, max_age_days=30, keep_at_least=1)
    service, repo = _backup_service(tmp_path, policy)
    now = datetime.now(UTC)
    recent = _backup(now - timedelta(days=2), "recent.db")
    old = _backup(now - timedelta(days=90), "old.db")
    recent_file = _seed_backup(repo, tmp_path, recent)
    old_file = _seed_backup(repo, tmp_path, old)

    result = service.prune()

    assert result.deleted == 1
    assert recent_file.exists()
    assert not old_file.exists()


def test_prune_keeps_row_when_file_delete_fails(tmp_path: Path) -> None:
    policy = RetentionPolicy(max_count=1, max_age_days=0, keep_at_least=1)
    service, repo = _backup_service(tmp_path, policy)
    newest = _backup(BASE + timedelta(days=1), "newest.db")
    oldest = _backup(BASE, "oldest.db")
    _seed_backup(repo, tmp_path, newest)
    repo.add(oldest)
    # The "file" for the prunable backup is actually a directory, so unlink raises OSError.
    (tmp_path / "oldest.db").mkdir()

    result = service.prune()

    assert (result.deleted, result.failed) == (0, 1)
    # Row kept so metadata still refers to something on disk (consistency preserved).
    assert repo.get(oldest.id) is not None


def test_disabled_backup_policy_is_a_noop(tmp_path: Path) -> None:
    service, repo = _backup_service(tmp_path, RetentionPolicy(max_count=0, max_age_days=0))
    for offset in range(5):
        _seed_backup(repo, tmp_path, _backup(BASE + timedelta(days=offset), f"b-{offset}.db"))
    result = service.prune()
    assert result.deleted == 0
    assert len(repo.list_all()) == 5


def test_none_policy_prunes_nothing(tmp_path: Path) -> None:
    service, repo = _backup_service(tmp_path, None)
    _seed_backup(repo, tmp_path, _backup(BASE, "b.db"))
    assert service.prune().deleted == 0
    assert len(repo.list_all()) == 1


# --------------------------------------------------------------- job pruning


def _job_service(policy: RetentionPolicy | None) -> tuple[JobService, InMemoryJobRepository]:
    repo = InMemoryJobRepository()
    service = JobService(
        repo,
        InMemoryChangeProposalRepository(),
        InMemoryApplicationRepository(),
        retention_policy=policy,
    )
    return service, repo


def _failed_backup_job(created_at: datetime, **overrides: object) -> Job:
    fields: dict = {
        "id": uuid4(),
        "job_type": JobType.BACKUP_CREATE,
        "target_entity_type": JobTargetType.DATABASE,
        "target_entity_id": None,
        "workspace_id": None,
        "status": JobStatus.FAILED,
        "attempt_count": 1,
        "payload": JobPayload(label="x"),
        "result_entity_type": None,
        "result_entity_id": None,
        "last_error": "boom",
        "created_at": created_at,
        "started_at": created_at,
        "finished_at": created_at,
    }
    fields.update(overrides)
    return Job(**fields)


def _queued_backup_job(created_at: datetime) -> Job:
    return Job(
        id=uuid4(),
        job_type=JobType.BACKUP_CREATE,
        target_entity_type=JobTargetType.DATABASE,
        target_entity_id=None,
        workspace_id=None,
        status=JobStatus.QUEUED,
        attempt_count=0,
        payload=JobPayload(label="q"),
        result_entity_type=None,
        result_entity_id=None,
        last_error=None,
        created_at=created_at,
        started_at=None,
        finished_at=None,
    )


def test_prune_jobs_removes_terminal_beyond_count() -> None:
    service, repo = _job_service(RetentionPolicy(max_count=2, max_age_days=0))
    for offset in range(4):
        repo.add(_failed_backup_job(BASE + timedelta(days=offset)))

    result = service.prune_jobs()

    assert (result.inspected, result.deleted, result.kept) == (4, 2, 2)
    assert len(repo.list_all()) == 2


def test_prune_jobs_never_touches_queued_or_running() -> None:
    service, repo = _job_service(RetentionPolicy(max_count=1, max_age_days=0))
    # Two queued jobs (older) plus one terminal (newest). count=1 keeps only the newest,
    # but queued jobs are not terminal and must survive regardless.
    repo.add(_queued_backup_job(BASE))
    repo.add(_queued_backup_job(BASE + timedelta(days=1)))
    repo.add(_failed_backup_job(BASE + timedelta(days=2)))

    result = service.prune_jobs()

    assert result.inspected == 1  # only the terminal job is a candidate
    assert result.deleted == 0  # it's the newest terminal, kept by count
    statuses = sorted(job.status.value for job in repo.list_all())
    assert statuses == ["failed", "queued", "queued"]


def test_prune_jobs_protects_referenced_retry_lineage() -> None:
    service, repo = _job_service(RetentionPolicy(max_count=1, max_age_days=0))
    original = _failed_backup_job(BASE)  # old, would be pruned by count=1
    child = _failed_backup_job(
        BASE + timedelta(days=5),
        retry_of_job_id=original.id,
        root_job_id=original.id,
    )
    repo.add(original)
    repo.add(child)

    result = service.prune_jobs()

    # child is the newest (kept by count); original is referenced by child, so it is kept
    # for lineage integrity rather than pruned.
    assert result.deleted == 0
    assert repo.get(original.id) is not None
    assert repo.get(child.id) is not None


def test_prune_jobs_deletes_unreferenced_old_job() -> None:
    service, repo = _job_service(RetentionPolicy(max_count=1, max_age_days=0))
    old = _failed_backup_job(BASE)
    new = _failed_backup_job(BASE + timedelta(days=5))
    repo.add(old)
    repo.add(new)

    result = service.prune_jobs()

    assert result.deleted == 1
    assert repo.get(old.id) is None
    assert repo.get(new.id) is not None


def test_disabled_job_policy_is_a_noop() -> None:
    service, repo = _job_service(RetentionPolicy(max_count=0, max_age_days=0))
    for offset in range(5):
        repo.add(_failed_backup_job(BASE + timedelta(days=offset)))
    assert service.prune_jobs().deleted == 0
    assert len(repo.list_all()) == 5
