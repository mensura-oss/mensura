"""Startup sweep that removes orphaned verification sandboxes.

Proposal verification runs inside a temporary Git worktree created by
:mod:`mensura_core.verification_sandbox` — a directory named ``mensura-verification-*``
that contains exactly one ``worktree`` child (a detached worktree of the workspace's
committed ``HEAD``). Each sandbox is removed after the verification completes, but a
crash or hard termination mid-verification can leave both the temp directory and its
stale ``.git/worktrees`` metadata behind.

Because Mensura is single-process, this sweep — run once in the startup lifespan, before
the job worker starts and before any traffic — can assume that **no verification is in
flight**. Any directory that still matches the Mensura sandbox naming scheme is therefore
necessarily orphaned by a previous process, which makes deletion safe.

The sweep is deliberately conservative:

* it only considers directories whose name starts with :data:`SANDBOX_TEMP_PREFIX`;
* it only deletes a directory whose layout matches what the factory creates — empty, or
  containing exactly one ``worktree`` child — never an arbitrary path;
* it relies on Git's own ``git worktree prune`` to drop stale metadata rather than
  hand-editing ``.git`` internals;
* every failure is logged as a warning and never aborts startup.
"""

import logging
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from git import Repo
from git.exc import GitError

from mensura_core.verification_sandbox import (
    SANDBOX_TEMP_PREFIX,
    SANDBOX_WORKTREE_DIRNAME,
    sandbox_parent_dir,
)

logger = logging.getLogger(__name__)

# A pruner runs ``git worktree prune`` for one workspace root, returning True on success.
WorktreePruner = Callable[[str], bool]


@dataclass(frozen=True)
class SandboxSweepSummary:
    """Outcome of a single startup sweep, for logging and tests."""

    inspected: int = 0
    """Candidate directories carrying the Mensura sandbox prefix that were examined."""
    removed: int = 0
    """Orphaned sandbox directories deleted."""
    skipped: int = 0
    """Candidates left in place (unexpected structure, or a deletion error)."""
    worktrees_pruned: int = 0
    """Workspaces whose stale Git worktree metadata was pruned via ``git worktree prune``."""


def is_mensura_sandbox_dir(path: Path) -> bool:
    """True only for a directory that matches the Mensura sandbox naming *and* layout.

    Conservative by construction: the name must carry the Mensura prefix, the entry must
    be a real directory (never a symlink), and its layout must be exactly what the factory
    creates — empty, or containing only a single ``worktree`` child. Anything else is not
    recognized as a sweepable sandbox and is left untouched.
    """
    if not path.name.startswith(SANDBOX_TEMP_PREFIX):
        return False
    if path.is_symlink() or not path.is_dir():
        return False
    try:
        children = list(path.iterdir())
    except OSError:
        return False
    if not children:
        return True
    return len(children) == 1 and children[0].name == SANDBOX_WORKTREE_DIRNAME


def find_sandbox_candidates(parent: Path) -> list[Path]:
    """Immediate children of ``parent`` whose name carries the Mensura sandbox prefix."""
    try:
        entries = sorted(parent.iterdir())
    except OSError:
        return []
    return [entry for entry in entries if entry.name.startswith(SANDBOX_TEMP_PREFIX)]


def _default_pruner(root: str) -> bool:
    repo = Repo(root, search_parent_directories=False)
    repo.git.worktree("prune")
    return True


class VerificationSandboxSweeper:
    """Remove orphaned verification sandboxes once, at process startup."""

    def __init__(
        self,
        *,
        parent_dir: Path | None = None,
        worktree_pruner: WorktreePruner = _default_pruner,
    ) -> None:
        self._parent_dir = parent_dir if parent_dir is not None else sandbox_parent_dir()
        self._prune = worktree_pruner

    def sweep(self, workspace_roots: Sequence[str] = ()) -> SandboxSweepSummary:
        """Delete orphaned sandbox directories, then prune stale worktree metadata.

        Directories are removed first so that the subsequent ``git worktree prune`` sees a
        missing working tree and cleanly drops the corresponding ``.git/worktrees`` entry.
        """
        removed, skipped = self._remove_orphaned_dirs()
        pruned = self._prune_worktree_metadata(workspace_roots)
        summary = SandboxSweepSummary(
            inspected=removed + skipped,
            removed=removed,
            skipped=skipped,
            worktrees_pruned=pruned,
        )
        logger.info(
            "Verification sandbox sweep complete: inspected=%d removed=%d skipped=%d "
            "worktrees_pruned=%d (parent=%s).",
            summary.inspected,
            summary.removed,
            summary.skipped,
            summary.worktrees_pruned,
            self._parent_dir,
        )
        return summary

    def _remove_orphaned_dirs(self) -> tuple[int, int]:
        removed = skipped = 0
        for candidate in find_sandbox_candidates(self._parent_dir):
            if not is_mensura_sandbox_dir(candidate):
                logger.warning(
                    "Skipping '%s': it carries the Mensura sandbox prefix but its structure is "
                    "unexpected; refusing to delete it.",
                    candidate,
                )
                skipped += 1
                continue
            try:
                shutil.rmtree(candidate)
            except OSError as error:
                logger.warning("Could not remove orphaned sandbox '%s': %s", candidate, error)
                skipped += 1
                continue
            logger.info("Removed orphaned verification sandbox '%s'.", candidate)
            removed += 1
        return removed, skipped

    def _prune_worktree_metadata(self, workspace_roots: Sequence[str]) -> int:
        pruned = 0
        for root in workspace_roots:
            try:
                if self._prune(root):
                    pruned += 1
            except (GitError, OSError) as error:
                logger.warning(
                    "Could not prune stale Git worktree metadata for '%s': %s", root, error
                )
        return pruned
