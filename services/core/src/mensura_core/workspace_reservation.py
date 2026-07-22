"""One process-wide, per-workspace reservation for live working-tree writers.

Only operations that mutate a workspace's live working tree (application apply and
undo) participate. They share a single :class:`WorkspaceWriteReservation` instance so
that at most one live-tree writer per workspace can run at a time, regardless of whether
the caller is a synchronous HTTP request or the background job worker (which invokes the
same service methods).

Operations that do not write the live tree deliberately do NOT participate:

* proposal verification materializes its sandbox from the committed ``HEAD`` and writes
  only inside a temporary worktree, so it is unaffected by concurrent live-tree writes;
* backup snapshots the SQLite database, not the workspace tree;
* standalone Guard reads the live tree and keeps its own guard-run reservation.

Contention never queues at this layer: a second claim for a workspace that is already
reserved is refused immediately with :class:`WorkspaceWriteInProgressError`.
"""

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from mensura_core.exceptions import WorkspaceWriteInProgressError

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class WorkspaceWriteHolder:
    """Diagnostics describing the operation currently holding a workspace reservation."""

    workspace_id: UUID
    holder_kind: str
    target_entity_type: str | None
    target_entity_id: UUID | None
    acquired_at: datetime


class WorkspaceWriteReservation:
    """Registry guaranteeing at most one live working-tree writer per workspace.

    The claim is atomic within the process (guarded by a single lock), released in a
    ``finally`` block by the context manager, and never silently queued: a competing
    writer for the same workspace is refused immediately.
    """

    def __init__(self, *, clock: Clock = _utc_now) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._holders: dict[UUID, WorkspaceWriteHolder] = {}

    @contextmanager
    def reserve(
        self,
        workspace_id: UUID,
        *,
        holder_kind: str,
        target_entity_type: str | None = None,
        target_entity_id: UUID | None = None,
    ) -> Iterator[WorkspaceWriteHolder]:
        """Reserve the workspace for a live-tree write, refusing a concurrent writer.

        Raises :class:`WorkspaceWriteInProgressError` immediately if the workspace is
        already reserved; otherwise records diagnostics and releases on exit.
        """
        holder = WorkspaceWriteHolder(
            workspace_id=workspace_id,
            holder_kind=holder_kind,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            acquired_at=self._clock(),
        )
        with self._lock:
            existing = self._holders.get(workspace_id)
            if existing is not None:
                raise WorkspaceWriteInProgressError(workspace_id, existing.holder_kind)
            self._holders[workspace_id] = holder
        try:
            yield holder
        finally:
            with self._lock:
                # Release only our own claim so a defensive double-exit cannot evict a
                # later holder that reused the same workspace id.
                if self._holders.get(workspace_id) is holder:
                    del self._holders[workspace_id]

    def is_reserved(self, workspace_id: UUID) -> bool:
        with self._lock:
            return workspace_id in self._holders

    def active_holders(self) -> tuple[WorkspaceWriteHolder, ...]:
        """A snapshot of the current holders, for diagnostics and tests."""
        with self._lock:
            return tuple(self._holders.values())
