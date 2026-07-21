"""Digest-checked, all-or-nothing atomic undo of text-file application changes.

Phase 1 (``_plan_undo``) verifies that every live target still matches the
recorded applied digest. Any drift blocks the entire undo before any write.

Phase 2 (``_commit_undo``) restores prior content via same-directory temp file
(flushed and fsynced) + atomic ``os.replace``, or removes created files via
``os.unlink``. No Git command is ever invoked and content is never re-generated.
"""

import os
import stat
import tempfile
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from mensura_core.application_models import ApplicationUndoFileEntry
from mensura_core.models import ChangeProposalChangeType
from mensura_core.safe_paths import resolve_safe_target
from mensura_core.undo_models import UndoFileAction, UndoFileOutcome

_DEFAULT_FILE_MODE = 0o644


@dataclass(frozen=True, slots=True)
class _PlannedUndoChange:
    entry: ApplicationUndoFileEntry
    target: Path
    observed_live_digest: str | None
    prior_content_restore_bytes: bytes | None  # None for CREATE (no restore, just delete)


@dataclass(frozen=True, slots=True)
class UndoWriteResult:
    outcomes: tuple[UndoFileOutcome, ...]
    partial: bool


def _digest(data: bytes) -> str:
    return f"sha256:{sha256(data).hexdigest()}"


def execute_undo(
    root: Path, undo_files: Sequence[ApplicationUndoFileEntry]
) -> UndoWriteResult:
    """Validate live digests against applied digests, then atomically undo.

    Raises :class:`UndoMetadataIncompleteError` when a file needs restoration
    but has truncated prior content. Raises :class:`UndoLiveDriftError` when
    the live digest doesn't match the recorded applied digest. Raises
    :class:`UndoUnsafePathError` when a path resolves unsafely.
    """
    plan = [_plan_undo(root, entry) for entry in undo_files]
    return _commit_undo(plan)


def _plan_undo(
    root: Path, entry: ApplicationUndoFileEntry
) -> "_PlannedUndoChange":
    from mensura_core.exceptions import (
        UndoLiveDriftError,
        UndoMetadataIncompleteError,
        UndoUnsafePathError,
    )

    target = resolve_safe_target(root, entry.path)
    if target is None:
        raise UndoUnsafePathError(entry.path)

    if entry.change_type is ChangeProposalChangeType.CREATE:
        if not target.exists() or target.is_symlink():
            raise UndoLiveDriftError(entry.path)
        live_bytes = target.read_bytes()
        live_digest = _digest(live_bytes)
        if entry.applied_digest is not None and live_digest != entry.applied_digest:
            raise UndoLiveDriftError(entry.path)
        return _PlannedUndoChange(
            entry=entry,
            target=target,
            observed_live_digest=live_digest,
            prior_content_restore_bytes=None,
        )

    if entry.change_type is ChangeProposalChangeType.DELETE:
        if target.exists():
            raise UndoLiveDriftError(entry.path)
        if entry.prior_truncated or entry.prior_content is None:
            raise UndoMetadataIncompleteError(entry.path)
        prior_bytes = entry.prior_content.encode("utf-8")
        return _PlannedUndoChange(
            entry=entry,
            target=target,
            observed_live_digest=None,
            prior_content_restore_bytes=prior_bytes,
        )

    if entry.change_type is ChangeProposalChangeType.MODIFY:
        if not target.exists() or not target.is_file():
            raise UndoLiveDriftError(entry.path)
        live_bytes = target.read_bytes()
        live_digest = _digest(live_bytes)
        if entry.applied_digest is not None and live_digest != entry.applied_digest:
            raise UndoLiveDriftError(entry.path)
        if entry.prior_truncated or entry.prior_content is None:
            raise UndoMetadataIncompleteError(entry.path)
        prior_bytes = entry.prior_content.encode("utf-8")
        return _PlannedUndoChange(
            entry=entry,
            target=target,
            observed_live_digest=live_digest,
            prior_content_restore_bytes=prior_bytes,
        )

    raise UndoLiveDriftError(entry.path)


def _stage_restore(planned: _PlannedUndoChange) -> Path:
    """Write the prior content to a fsynced same-directory temp file for atomic replace."""
    target = planned.target
    parent_dir = target.parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=".mensura-undo-", dir=parent_dir)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(planned.prior_content_restore_bytes or b"")
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists() and not target.is_symlink():
            os.chmod(temp_path, stat.S_IMODE(target.stat().st_mode))
        else:
            os.chmod(temp_path, _DEFAULT_FILE_MODE)
    except OSError:
        with suppress(OSError):
            temp_path.unlink()
        raise
    return temp_path


def _commit_undo(plan: list[_PlannedUndoChange]) -> UndoWriteResult:
    from mensura_core.exceptions import UndoWriteError

    staged: dict[int, Path] = {}
    try:
        for index, planned in enumerate(plan):
            if planned.prior_content_restore_bytes is not None:
                staged[index] = _stage_restore(planned)
    except OSError as error:
        for temp_path in staged.values():
            with suppress(OSError):
                temp_path.unlink()
        raise UndoWriteError() from error

    outcomes: list[UndoFileOutcome] = []
    partial = False
    for index, planned in enumerate(plan):
        if partial:
            outcomes.append(
                _outcome_skipped(planned, "Another file failed to undo first.")
            )
            continue
        try:
            if planned.entry.change_type is ChangeProposalChangeType.CREATE:
                planned.target.unlink()
                outcomes.append(
                    _outcome_done(
                        planned,
                        prior_restored_digest=None,
                        reason="Created file removed.",
                    )
                )
            elif planned.entry.change_type in (
                ChangeProposalChangeType.MODIFY,
                ChangeProposalChangeType.DELETE,
            ):
                os.replace(staged[index], planned.target)
                prior_restored_digest = (
                    _digest(planned.prior_content_restore_bytes)
                    if planned.prior_content_restore_bytes is not None
                    else None
                )
                reason = (
                    "Deleted file restored from prior content."
                    if planned.entry.change_type is ChangeProposalChangeType.DELETE
                    else "Prior content restored atomically."
                )
                outcomes.append(
                    _outcome_done(
                        planned,
                        prior_restored_digest=prior_restored_digest,
                        reason=reason,
                    )
                )
        except OSError:
            partial = True
            outcomes.append(
                _outcome_failed(planned, "OS write failed during undo commit.")
            )

    for temp_path in staged.values():
        if temp_path.exists():
            with suppress(OSError):
                temp_path.unlink()

    return UndoWriteResult(outcomes=tuple(outcomes), partial=partial)


def _outcome_done(
    planned: _PlannedUndoChange, *, prior_restored_digest: str | None, reason: str
) -> UndoFileOutcome:
    entry = planned.entry
    if entry.change_type is ChangeProposalChangeType.CREATE:
        action = UndoFileAction.DELETED
    else:
        action = UndoFileAction.RESTORED
    return UndoFileOutcome(
        path=entry.path,
        change_type=entry.change_type,
        undone=True,
        action=action,
        expected_applied_digest=entry.applied_digest,
        observed_live_digest=planned.observed_live_digest,
        prior_digest_restored=prior_restored_digest,
        reason=reason,
    )


def _outcome_failed(
    planned: _PlannedUndoChange, reason: str
) -> UndoFileOutcome:
    entry = planned.entry
    return UndoFileOutcome(
        path=entry.path,
        change_type=entry.change_type,
        undone=False,
        action=UndoFileAction.FAILED,
        expected_applied_digest=entry.applied_digest,
        observed_live_digest=planned.observed_live_digest,
        prior_digest_restored=None,
        reason=reason,
    )


def _outcome_skipped(
    planned: _PlannedUndoChange, reason: str
) -> UndoFileOutcome:
    entry = planned.entry
    return UndoFileOutcome(
        path=entry.path,
        change_type=entry.change_type,
        undone=False,
        action=UndoFileAction.REFUSED,
        expected_applied_digest=entry.applied_digest,
        observed_live_digest=planned.observed_live_digest,
        prior_digest_restored=None,
        reason=reason,
    )
