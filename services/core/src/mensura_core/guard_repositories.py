from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.guard_models import GuardRunResponse


class GuardRunRepository(Protocol):
    def get_latest(self, workspace_id: UUID) -> GuardRunResponse | None: ...

    def save_latest(self, run: GuardRunResponse) -> None: ...


class InMemoryGuardRunRepository:
    """Process-local latest Guard result storage."""

    def __init__(self) -> None:
        self._latest_by_workspace: dict[UUID, GuardRunResponse] = {}
        self._lock = RLock()

    def get_latest(self, workspace_id: UUID) -> GuardRunResponse | None:
        with self._lock:
            return self._latest_by_workspace.get(workspace_id)

    def save_latest(self, run: GuardRunResponse) -> None:
        with self._lock:
            self._latest_by_workspace[run.workspace_id] = run
