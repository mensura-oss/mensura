"""Unit tests for the unified per-workspace live-tree write reservation."""

import threading
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from mensura_core.exceptions import WorkspaceWriteInProgressError
from mensura_core.workspace_reservation import WorkspaceWriteReservation


def test_reserve_yields_holder_with_diagnostics() -> None:
    reservation = WorkspaceWriteReservation()
    workspace_id = uuid4()
    target_id = uuid4()

    with reservation.reserve(
        workspace_id,
        holder_kind="application_apply",
        target_entity_type="change_proposal",
        target_entity_id=target_id,
    ) as holder:
        assert holder.workspace_id == workspace_id
        assert holder.holder_kind == "application_apply"
        assert holder.target_entity_type == "change_proposal"
        assert holder.target_entity_id == target_id
        assert isinstance(holder.acquired_at, datetime)
        assert reservation.is_reserved(workspace_id)
        assert reservation.active_holders() == (holder,)


def test_second_claim_on_same_workspace_is_refused_immediately() -> None:
    reservation = WorkspaceWriteReservation()
    workspace_id = uuid4()

    # The middle pytest.raises catches the third context manager's refusal on entry.
    with (
        reservation.reserve(workspace_id, holder_kind="application_apply"),
        pytest.raises(WorkspaceWriteInProgressError) as excinfo,
        reservation.reserve(workspace_id, holder_kind="application_undo"),
    ):
        pytest.fail("The second reservation must not be granted.")

    # The error names the workspace and the holder that is already active.
    assert excinfo.value.workspace_id == workspace_id
    assert excinfo.value.holder_kind == "application_apply"


def test_distinct_workspaces_do_not_contend() -> None:
    reservation = WorkspaceWriteReservation()
    first, second = uuid4(), uuid4()

    with (
        reservation.reserve(first, holder_kind="application_apply"),
        reservation.reserve(second, holder_kind="application_undo"),
    ):
        assert reservation.is_reserved(first)
        assert reservation.is_reserved(second)
        assert len(reservation.active_holders()) == 2


def test_reservation_is_released_on_normal_exit() -> None:
    reservation = WorkspaceWriteReservation()
    workspace_id = uuid4()

    with reservation.reserve(workspace_id, holder_kind="application_apply"):
        assert reservation.is_reserved(workspace_id)
    assert not reservation.is_reserved(workspace_id)
    assert reservation.active_holders() == ()

    # The workspace can be claimed again once released.
    with reservation.reserve(workspace_id, holder_kind="application_undo"):
        assert reservation.is_reserved(workspace_id)


def test_reservation_is_released_even_when_body_raises() -> None:
    reservation = WorkspaceWriteReservation()
    workspace_id = uuid4()

    with pytest.raises(RuntimeError):  # noqa: SIM117 — asserting the body raise, then re-claim below
        with reservation.reserve(workspace_id, holder_kind="application_apply"):
            raise RuntimeError("boom")

    assert not reservation.is_reserved(workspace_id)
    # A refused claim does not leave the earlier holder registered either.
    with (
        reservation.reserve(workspace_id, holder_kind="application_apply"),
        pytest.raises(WorkspaceWriteInProgressError),
        reservation.reserve(workspace_id, holder_kind="application_undo"),
    ):
        pass
    assert not reservation.is_reserved(workspace_id)


def test_reservation_is_not_reentrant_for_the_same_workspace() -> None:
    """A holder cannot re-enter its own workspace: nested live-tree writes are a bug."""
    reservation = WorkspaceWriteReservation()
    workspace_id = uuid4()

    with (
        reservation.reserve(workspace_id, holder_kind="application_apply"),
        pytest.raises(WorkspaceWriteInProgressError),
        reservation.reserve(workspace_id, holder_kind="application_apply"),
    ):
        pass


def test_uses_injected_clock_for_acquired_at() -> None:
    fixed = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)
    reservation = WorkspaceWriteReservation(clock=lambda: fixed)
    with reservation.reserve(uuid4(), holder_kind="application_apply") as holder:
        assert holder.acquired_at == fixed


def test_concurrent_writers_are_mutually_exclusive_across_threads() -> None:
    """One thread holds the reservation; a second thread is refused deterministically."""
    reservation = WorkspaceWriteReservation()
    workspace_id = uuid4()
    holding = threading.Event()
    may_release = threading.Event()
    refused: list[bool] = []

    def hold() -> None:
        with reservation.reserve(workspace_id, holder_kind="application_apply"):
            holding.set()
            may_release.wait(timeout=5)

    holder_thread = threading.Thread(target=hold)
    holder_thread.start()
    assert holding.wait(timeout=5)
    try:
        with reservation.reserve(workspace_id, holder_kind="application_undo"):
            refused.append(False)
    except WorkspaceWriteInProgressError:
        refused.append(True)
    finally:
        may_release.set()
        holder_thread.join(timeout=5)

    assert refused == [True]
    assert not reservation.is_reserved(workspace_id)
