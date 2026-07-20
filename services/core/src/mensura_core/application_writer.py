"""Digest-checked, all-or-nothing atomic application of proposal changes.

Phase 1 (``_plan``) resolves every safe live path and compares the observed live
digest against the proposal's captured before-digest, refusing the whole
application before any write when a path is unsafe or the live tree drifted.
Phase 2 (``_commit``) stages each create/modify body to a same-directory temp
file (flushed and fsynced) and then commits atomic ``os.replace``/``os.unlink``.
No Git command is ever invoked and content is never re-generated.
"""

import os
import stat
import tempfile
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from mensura_core.application_models import (
    APPLICATION_UNDO_CONTENT_MAX_BYTES_PER_FILE,
    ApplicationUndoFileEntry,
    AppliedFileReason,
    AppliedFileResult,
)
from mensura_core.change_proposal_models import ChangeProposalFileChange
from mensura_core.exceptions import (
    ApplicationLiveDriftError,
    ApplicationUnsafePathError,
    ApplicationWriteError,
)
from mensura_core.models import ChangeProposalChangeType
from mensura_core.safe_paths import resolve_safe_target

_CREATED_FILE_MODE = 0o644


@dataclass(frozen=True, slots=True)
class _PlannedChange:
    change: ChangeProposalFileChange
    target: Path
    prior_existed: bool
    prior_digest: str | None
    prior_content: str | None
    prior_content_bytes: int
    prior_truncated: bool
    payload: bytes | None
    applied_digest: str | None


@dataclass(frozen=True, slots=True)
class ApplicationWriteResult:
    file_results: tuple[AppliedFileResult, ...]
    undo_files: tuple[ApplicationUndoFileEntry, ...]
    partial: bool


def apply_proposal_changes(
    root: Path, changes: Sequence[ChangeProposalFileChange]
) -> ApplicationWriteResult:
    """Validate live digests, then atomically apply changes to the live tree.

    Raises :class:`ApplicationUnsafePathError` or :class:`ApplicationLiveDriftError`
    before writing anything when the live tree is unsafe or drifted, and
    :class:`ApplicationWriteError` if staging fails before any live file changed.
    """
    plan = [_plan_change(root, change) for change in changes]
    return _commit(plan)


def _digest(data: bytes) -> str:
    return f"sha256:{sha256(data).hexdigest()}"


def _capture_prior(live_bytes: bytes) -> tuple[str | None, int, bool]:
    """Return bounded UTF-8 prior content for undo, or a truncation flag."""
    if len(live_bytes) > APPLICATION_UNDO_CONTENT_MAX_BYTES_PER_FILE:
        return None, len(live_bytes), True
    try:
        return live_bytes.decode("utf-8"), len(live_bytes), False
    except UnicodeDecodeError:
        return None, len(live_bytes), True


def _plan_change(root: Path, change: ChangeProposalFileChange) -> _PlannedChange:
    target = resolve_safe_target(root, change.path)
    if target is None:
        raise ApplicationUnsafePathError(change.path)

    if change.change_type is ChangeProposalChangeType.CREATE:
        if target.exists() or target.is_symlink():
            raise ApplicationLiveDriftError(change.path)
        payload = (change.proposed_text or "").encode("utf-8")
        return _PlannedChange(
            change=change,
            target=target,
            prior_existed=False,
            prior_digest=None,
            prior_content=None,
            prior_content_bytes=0,
            prior_truncated=False,
            payload=payload,
            applied_digest=_digest(payload),
        )

    if not target.exists() or not target.is_file():
        raise ApplicationLiveDriftError(change.path)
    live_bytes = target.read_bytes()
    live_digest = _digest(live_bytes)
    if live_digest != change.before_digest:
        raise ApplicationLiveDriftError(change.path)
    prior_content, prior_content_bytes, prior_truncated = _capture_prior(live_bytes)

    if change.change_type is ChangeProposalChangeType.DELETE:
        payload = None
        applied_digest = None
    else:
        payload = (change.proposed_text or "").encode("utf-8")
        applied_digest = _digest(payload)
    return _PlannedChange(
        change=change,
        target=target,
        prior_existed=True,
        prior_digest=live_digest,
        prior_content=prior_content,
        prior_content_bytes=prior_content_bytes,
        prior_truncated=prior_truncated,
        payload=payload,
        applied_digest=applied_digest,
    )


def _stage(planned: _PlannedChange) -> Path:
    """Write the payload to a fsynced same-directory temp file for atomic replace."""
    target = planned.target
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=".mensura-apply-", dir=target.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(planned.payload or b"")
            handle.flush()
            os.fsync(handle.fileno())
        if planned.prior_existed:
            os.chmod(temp_path, stat.S_IMODE(target.stat().st_mode))
        else:
            os.chmod(temp_path, _CREATED_FILE_MODE)
    except OSError:
        with suppress(OSError):
            temp_path.unlink()
        raise
    return temp_path


def _commit(plan: list[_PlannedChange]) -> ApplicationWriteResult:
    staged: dict[int, Path] = {}
    try:
        for index, planned in enumerate(plan):
            if planned.payload is not None:
                staged[index] = _stage(planned)
    except OSError as error:
        for temp_path in staged.values():
            with suppress(OSError):
                temp_path.unlink()
        raise ApplicationWriteError() from error

    file_results: list[AppliedFileResult] = []
    undo_files: list[ApplicationUndoFileEntry] = []
    partial = False
    for index, planned in enumerate(plan):
        if partial:
            file_results.append(
                _result(planned, applied=False, reason=AppliedFileReason.NOT_ATTEMPTED)
            )
            continue
        try:
            if planned.change.change_type is ChangeProposalChangeType.DELETE:
                planned.target.unlink()
            else:
                os.replace(staged[index], planned.target)
        except OSError:
            partial = True
            file_results.append(
                _result(planned, applied=False, reason=AppliedFileReason.WRITE_FAILED)
            )
            continue
        file_results.append(_result(planned, applied=True, reason=AppliedFileReason.APPLIED))
        undo_files.append(_undo_entry(planned))

    for temp_path in staged.values():
        if temp_path.exists():
            with suppress(OSError):
                temp_path.unlink()

    return ApplicationWriteResult(
        file_results=tuple(file_results),
        undo_files=tuple(undo_files),
        partial=partial,
    )


def _result(
    planned: _PlannedChange, *, applied: bool, reason: AppliedFileReason
) -> AppliedFileResult:
    change = planned.change
    return AppliedFileResult(
        path=change.path,
        change_type=change.change_type,
        before_digest=change.before_digest,
        live_before_digest=planned.prior_digest,
        after_digest=change.after_digest,
        applied_digest=planned.applied_digest if applied else None,
        applied=applied,
        reason=reason,
    )


def _undo_entry(planned: _PlannedChange) -> ApplicationUndoFileEntry:
    change = planned.change
    return ApplicationUndoFileEntry(
        path=change.path,
        change_type=change.change_type,
        prior_existed=planned.prior_existed,
        prior_digest=planned.prior_digest,
        prior_content=planned.prior_content,
        prior_content_bytes=planned.prior_content_bytes,
        prior_truncated=planned.prior_truncated,
        applied_digest=planned.applied_digest,
    )
