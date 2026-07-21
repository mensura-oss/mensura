from collections.abc import Sequence
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.undo_models import UndoArtifact


class UndoRepository(Protocol):
    def save_if_absent_for_application(self, undo: UndoArtifact) -> bool: ...

    def get(self, undo_id: UUID) -> UndoArtifact | None: ...

    def get_for_application(self, application_id: UUID) -> UndoArtifact | None: ...

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[UndoArtifact]: ...


class InMemoryUndoRepository:
    """Process-local storage with single-undo semantics per application."""

    def __init__(self) -> None:
        self._undos: dict[UUID, UndoArtifact] = {}
        self._undo_ids_by_application: dict[UUID, UUID] = {}
        self._lock = RLock()

    def save_if_absent_for_application(self, undo: UndoArtifact) -> bool:
        with self._lock:
            if undo.application_id in self._undo_ids_by_application:
                return False
            self._undos[undo.id] = undo
            self._undo_ids_by_application[undo.application_id] = undo.id
            return True

    def get(self, undo_id: UUID) -> UndoArtifact | None:
        with self._lock:
            return self._undos.get(undo_id)

    def get_for_application(self, application_id: UUID) -> UndoArtifact | None:
        with self._lock:
            undo_id = self._undo_ids_by_application.get(application_id)
            return self._undos.get(undo_id) if undo_id is not None else None

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[UndoArtifact]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        undo
                        for undo in self._undos.values()
                        if undo.workspace_id == workspace_id
                    ),
                    key=lambda undo: (undo.created_at, undo.id),
                )
            )
