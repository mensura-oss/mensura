from collections.abc import Sequence
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.context_pack_models import ContextPackManifest


class ContextPackRepository(Protocol):
    def save_if_absent(self, manifest: ContextPackManifest) -> bool: ...

    def get(self, workspace_id: UUID, context_pack_id: str) -> ContextPackManifest | None: ...

    def find_by_id(self, context_pack_id: str) -> ContextPackManifest | None: ...

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[ContextPackManifest]: ...


class InMemoryContextPackRepository:
    """Process-local immutable context-pack storage keyed by content-derived id."""

    def __init__(self) -> None:
        self._manifests: dict[tuple[UUID, str], ContextPackManifest] = {}
        self._lock = RLock()

    def save_if_absent(self, manifest: ContextPackManifest) -> bool:
        key = (manifest.workspace_id, manifest.id)
        with self._lock:
            if key in self._manifests:
                return False
            self._manifests[key] = manifest
            return True

    def get(self, workspace_id: UUID, context_pack_id: str) -> ContextPackManifest | None:
        with self._lock:
            return self._manifests.get((workspace_id, context_pack_id))

    def find_by_id(self, context_pack_id: str) -> ContextPackManifest | None:
        with self._lock:
            return next(
                (
                    manifest
                    for (_, stored_id), manifest in self._manifests.items()
                    if stored_id == context_pack_id
                ),
                None,
            )

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[ContextPackManifest]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        manifest
                        for (stored_workspace_id, _), manifest in self._manifests.items()
                        if stored_workspace_id == workspace_id
                    ),
                    key=lambda manifest: manifest.id,
                )
            )
