from collections.abc import Sequence
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.backup_models import BackupArtifact


class BackupRepository(Protocol):
    def add(self, backup: BackupArtifact) -> None: ...

    def get(self, backup_id: UUID) -> BackupArtifact | None: ...

    def list_all(self) -> Sequence[BackupArtifact]: ...

    def delete(self, backup_id: UUID) -> bool:
        """Remove one backup's metadata row. Returns True if a row was deleted."""
        ...


class InMemoryBackupRepository:
    def __init__(self) -> None:
        self._backups: dict[UUID, BackupArtifact] = {}
        self._lock = RLock()

    def add(self, backup: BackupArtifact) -> None:
        with self._lock:
            self._backups[backup.id] = backup

    def get(self, backup_id: UUID) -> BackupArtifact | None:
        with self._lock:
            return self._backups.get(backup_id)

    def delete(self, backup_id: UUID) -> bool:
        with self._lock:
            return self._backups.pop(backup_id, None) is not None

    def list_all(self) -> Sequence[BackupArtifact]:
        with self._lock:
            return tuple(
                sorted(
                    self._backups.values(),
                    key=lambda b: (b.created_at, b.id),
                    reverse=True,
                )
            )
