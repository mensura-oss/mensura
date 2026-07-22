import contextlib
import hashlib
import logging
import os
import shutil
import sqlite3
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import Engine, text

from mensura_core.backup_models import (
    BackupArtifact,
    BackupCollection,
    BackupStatus,
)
from mensura_core.backup_repositories import BackupRepository
from mensura_core.event_publisher import EventPublisher, MensuraEvent
from mensura_core.exceptions import (
    BackupIntegrityError,
    BackupNotCompletedError,
    BackupNotFoundError,
    BackupRestoreError,
    BackupWriteError,
)
from mensura_core.models import ensure_utc_timestamp
from mensura_core.persistence.database import get_alembic_head
from mensura_core.retention import RetentionPolicy, RetentionResult
from mensura_core.service import utc_now

logger = logging.getLogger(__name__)


def _compute_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


class BackupService:
    def __init__(
        self,
        backup_repository: BackupRepository,
        backup_dir: Path,
        engine: Engine | None = None,
        db_path: Path | None = None,
        *,
        event_publisher: EventPublisher | None = None,
        retention_policy: RetentionPolicy | None = None,
    ) -> None:
        self._engine = engine
        self._repo = backup_repository
        self._backup_dir = backup_dir
        self._db_path = db_path
        self._event_publisher = event_publisher
        self._retention = retention_policy

    def create_backup(self, label: str | None = None) -> BackupArtifact:
        if self._engine is None:
            raise BackupWriteError(
                "Backups are only available with SQLite persistence (use_sql=True)."
            )
        backup_dir = self._backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)

        now = utc_now()
        db_version = get_alembic_head()

        timestamp = now.strftime("%Y-%m-%dT%H%M%SZ")
        short_id = str(uuid4())[:8]
        filename = f"backup-{timestamp}-{short_id}.db"
        backup_path = backup_dir / filename

        try:
            raw_connection = self._engine.raw_connection()
            try:
                src = raw_connection.driver_connection
                dst = sqlite3.connect(str(backup_path))
                try:
                    src.backup(dst)
                finally:
                    dst.close()
            finally:
                raw_connection.close()

            sha256_hex = _compute_sha256(backup_path)
            file_size = backup_path.stat().st_size

            artifact = BackupArtifact(
                id=uuid4(),
                created_at=ensure_utc_timestamp(now),
                db_version=db_version,
                file_size_bytes=file_size,
                sha256_hex=sha256_hex,
                storage_path=filename,
                status=BackupStatus.COMPLETED,
                label=label,
                error_message=None,
            )
            self._repo.add(artifact)
            logger.info(
                "Backup created: %s (%d bytes, %s)", artifact.id, file_size, sha256_hex[:12]
            )
            self._publish_backup_event(artifact)
            # Bound the backup directory as new backups arrive. Best-effort: a retention
            # failure must never fail the backup that was just successfully written.
            try:
                self.prune()
            except Exception:
                logger.warning("Backup retention pruning failed after create.", exc_info=True)
            return artifact

        except Exception as exc:
            if backup_path.exists():
                with contextlib.suppress(OSError):
                    backup_path.unlink()

            artifact = BackupArtifact(
                id=uuid4(),
                created_at=ensure_utc_timestamp(now),
                db_version=db_version,
                file_size_bytes=0,
                sha256_hex="",
                storage_path=filename,
                status=BackupStatus.FAILED,
                label=label,
                error_message=str(exc),
            )
            self._repo.add(artifact)
            raise BackupWriteError(f"Failed to create backup: {exc}") from exc

    def prune(self) -> RetentionResult:
        """Delete backups beyond the retention policy. Best-effort, never raises for a
        single failed deletion.

        The newest backup is always kept (``keep_at_least=1``), so this never removes the
        user's only backup. For each prunable backup the file is unlinked **before** the
        metadata row is deleted, and a file-unlink failure skips the row deletion — so a
        surviving row always still refers to its file.
        """
        if self._retention is None or not self._retention.enabled:
            return RetentionResult()
        backups = tuple(self._repo.list_all())
        kept, prunable = self._retention.partition(
            backups, now=utc_now(), timestamp=lambda b: b.created_at
        )
        deleted = failed = 0
        for backup in prunable:
            file_path = self._backup_dir / backup.storage_path
            try:
                file_path.unlink(missing_ok=True)
            except OSError as error:
                logger.warning(
                    "Retention: could not delete backup file '%s' (%s); keeping its metadata.",
                    file_path,
                    error,
                )
                failed += 1
                continue
            try:
                self._repo.delete(backup.id)
            except Exception:
                logger.warning(
                    "Retention: deleted backup file '%s' but could not delete its row %s.",
                    file_path,
                    backup.id,
                    exc_info=True,
                )
                failed += 1
                continue
            logger.info(
                "Retention: pruned backup %s (workspace=n/a, createdAt=%s, path=%s).",
                backup.id,
                backup.created_at.isoformat(),
                backup.storage_path,
            )
            deleted += 1
        return RetentionResult(
            inspected=len(backups), deleted=deleted, kept=len(kept), failed=failed
        )

    def get_backup(self, backup_id: UUID) -> BackupArtifact:
        backup = self._repo.get(backup_id)
        if backup is None:
            raise BackupNotFoundError(backup_id)
        return backup

    def list_backups(self) -> BackupCollection:
        items = self._repo.list_all()
        return BackupCollection(items=tuple(items), total=len(items))

    def _publish_backup_event(self, artifact: BackupArtifact) -> None:
        if self._event_publisher is None:
            return
        summary = f"Backup {artifact.status.value}. Size: {artifact.file_size_bytes} bytes."
        self._event_publisher.publish(
            MensuraEvent(
                event_type="backup.created",
                workspace_id=None,
                entity_type="backup",
                entity_id=artifact.id,
                status=artifact.status.value,
                summary=summary,
            )
        )

    def restore_backup(self, backup_id: UUID) -> str:
        if self._engine is None or self._db_path is None:
            raise BackupRestoreError(
                "Restore is only available with SQLite persistence (use_sql=True)."
            )
        backup = self._repo.get(backup_id)
        if backup is None:
            raise BackupNotFoundError(backup_id)

        if backup.status != BackupStatus.COMPLETED:
            raise BackupNotCompletedError(backup_id)

        backup_file = self._backup_dir / backup.storage_path
        if not backup_file.exists():
            raise BackupIntegrityError(
                backup_id,
                f"Backup file '{backup.storage_path}' is missing from disk.",
            )

        actual_digest = _compute_sha256(backup_file)
        if actual_digest != backup.sha256_hex:
            raise BackupIntegrityError(
                backup_id,
                f"SHA-256 mismatch. Stored: {backup.sha256_hex[:16]}..., "
                f"Actual: {actual_digest[:16]}...",
            )

        db_path = self._db_path

        try:
            with self._engine.connect() as conn:
                conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
                conn.commit()
        except Exception as exc:
            raise BackupRestoreError(f"WAL checkpoint failed: {exc}") from exc

        self._engine.dispose()

        wal_path = Path(str(db_path) + "-wal")
        shm_path = Path(str(db_path) + "-shm")

        backup_temp = db_path.parent / f".mensura-restore-{uuid4().hex[:8]}.tmp"
        try:
            shutil.copy2(str(backup_file), str(backup_temp))
            os.replace(str(backup_temp), str(db_path))
        except OSError as exc:
            with contextlib.suppress(OSError):
                backup_temp.unlink()
            raise BackupRestoreError(
                f"Failed to replace database with backup: {exc}"
            ) from exc

        for path in (wal_path, shm_path):
            with contextlib.suppress(OSError):
                path.unlink(missing_ok=True)

        logger.info(
            "Database restored from backup %s (%s). Core must be restarted.",
            backup_id,
            backup.storage_path,
        )
        return (
            "Database restored. Please restart Mensura Core "
            "for the restored state to take effect."
        )
