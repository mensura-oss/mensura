from dataclasses import dataclass
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.vault_models import VaultFileInventoryItem, VaultInventorySnapshot


@dataclass(frozen=True, slots=True)
class VaultInventoryRecord:
    snapshot: VaultInventorySnapshot
    items: tuple[VaultFileInventoryItem, ...]


class VaultInventoryRepository(Protocol):
    def get_latest(self, workspace_id: UUID) -> VaultInventoryRecord | None: ...

    def save_latest(self, record: VaultInventoryRecord) -> None: ...


class InMemoryVaultInventoryRepository:
    """Process-local latest Vault inventory storage."""

    def __init__(self) -> None:
        self._latest_by_workspace: dict[UUID, VaultInventoryRecord] = {}
        self._lock = RLock()

    def get_latest(self, workspace_id: UUID) -> VaultInventoryRecord | None:
        with self._lock:
            return self._latest_by_workspace.get(workspace_id)

    def save_latest(self, record: VaultInventoryRecord) -> None:
        with self._lock:
            self._latest_by_workspace[record.snapshot.workspace_id] = record
