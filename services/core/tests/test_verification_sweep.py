"""Unit tests for the orphaned verification-sandbox startup sweep."""

import logging
import os
from pathlib import Path

import pytest
from git import Repo

from mensura_core.verification_sweep import (
    VerificationSandboxSweeper,
    find_sandbox_candidates,
    is_mensura_sandbox_dir,
)

SANDBOX_NAME = "mensura-verification-deadbeef"


class RecordingPruner:
    """A fake ``git worktree prune`` that records the roots it was asked to prune."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, root: str) -> bool:
        self.calls.append(root)
        return True


def _make_sandbox(parent: Path, name: str = SANDBOX_NAME, *, with_worktree: bool = True) -> Path:
    directory = parent / name
    directory.mkdir()
    if with_worktree:
        (directory / "worktree").mkdir()
    return directory


def _init_repo(root: Path) -> Repo:
    repo = Repo.init(root)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Mensura Test")
        config.set_value("user", "email", "test@mensura.invalid")
    (root / "file.txt").write_text("hello\n", encoding="utf-8")
    repo.git.add("-A")
    repo.git.commit("-m", "baseline")
    return repo


# ------------------------------------------------------------------- detection logic


def test_recognizes_empty_and_worktree_only_sandboxes(tmp_path: Path) -> None:
    empty = _make_sandbox(tmp_path, "mensura-verification-empty", with_worktree=False)
    with_worktree = _make_sandbox(tmp_path, "mensura-verification-full")
    assert is_mensura_sandbox_dir(empty)
    assert is_mensura_sandbox_dir(with_worktree)


def test_rejects_non_prefixed_and_unexpected_structures(tmp_path: Path) -> None:
    # Wrong name.
    unrelated = tmp_path / "some-other-tempdir"
    unrelated.mkdir()
    assert not is_mensura_sandbox_dir(unrelated)

    # Correct prefix but an unexpected extra file — must NOT be recognized as sweepable.
    tampered = _make_sandbox(tmp_path, "mensura-verification-tampered")
    (tampered / "secret.txt").write_text("keep me", encoding="utf-8")
    assert not is_mensura_sandbox_dir(tampered)

    # A file (not a directory) that happens to carry the prefix.
    prefixed_file = tmp_path / "mensura-verification-file"
    prefixed_file.write_text("not a dir", encoding="utf-8")
    assert not is_mensura_sandbox_dir(prefixed_file)


def test_rejects_symlink_even_with_prefix(tmp_path: Path) -> None:
    real = _make_sandbox(tmp_path, "mensura-verification-real")
    link = tmp_path / "mensura-verification-link"
    os.symlink(real, link)
    assert not is_mensura_sandbox_dir(link)


def test_find_candidates_matches_prefix_only(tmp_path: Path) -> None:
    _make_sandbox(tmp_path, "mensura-verification-a")
    _make_sandbox(tmp_path, "mensura-verification-b", with_worktree=False)
    (tmp_path / "unrelated").mkdir()
    candidates = {path.name for path in find_sandbox_candidates(tmp_path)}
    assert candidates == {"mensura-verification-a", "mensura-verification-b"}


def test_find_candidates_on_missing_parent_is_empty(tmp_path: Path) -> None:
    assert find_sandbox_candidates(tmp_path / "does-not-exist") == []


# ------------------------------------------------------------------- sweep behavior


def test_sweep_removes_orphaned_dirs_and_prunes_each_workspace(tmp_path: Path) -> None:
    _make_sandbox(tmp_path, "mensura-verification-a")
    _make_sandbox(tmp_path, "mensura-verification-b", with_worktree=False)
    (tmp_path / "unrelated-dir").mkdir()
    pruner = RecordingPruner()

    sweeper = VerificationSandboxSweeper(parent_dir=tmp_path, worktree_pruner=pruner)
    summary = sweeper.sweep(["/ws/one", "/ws/two"])

    assert (summary.inspected, summary.removed, summary.skipped) == (2, 2, 0)
    assert summary.worktrees_pruned == 2
    assert pruner.calls == ["/ws/one", "/ws/two"]
    assert not (tmp_path / "mensura-verification-a").exists()
    assert not (tmp_path / "mensura-verification-b").exists()
    assert (tmp_path / "unrelated-dir").exists()  # untouched


def test_sweep_refuses_unexpected_structure_and_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    tampered = _make_sandbox(tmp_path, "mensura-verification-tampered")
    (tampered / "secret.txt").write_text("do not delete", encoding="utf-8")

    sweeper = VerificationSandboxSweeper(parent_dir=tmp_path, worktree_pruner=RecordingPruner())
    with caplog.at_level(logging.WARNING):
        summary = sweeper.sweep()

    assert (summary.inspected, summary.removed, summary.skipped) == (1, 0, 1)
    assert tampered.exists()  # never deleted
    assert (tampered / "secret.txt").read_text(encoding="utf-8") == "do not delete"
    assert any("unexpected" in record.getMessage() for record in caplog.records)


def test_sweep_is_idempotent(tmp_path: Path) -> None:
    _make_sandbox(tmp_path, "mensura-verification-a")
    sweeper = VerificationSandboxSweeper(parent_dir=tmp_path, worktree_pruner=RecordingPruner())

    first = sweeper.sweep()
    second = sweeper.sweep()

    assert first.removed == 1
    assert (second.inspected, second.removed, second.skipped) == (0, 0, 0)


def test_sweep_swallows_prune_errors_for_bad_roots(tmp_path: Path) -> None:
    # The real default pruner opens Repo(root); a non-git root raises, which is swallowed.
    sweeper = VerificationSandboxSweeper(parent_dir=tmp_path)
    summary = sweeper.sweep([str(tmp_path / "not-a-repo")])
    assert summary.worktrees_pruned == 0


# --------------------------------------------------- end-to-end with a real git worktree


def test_sweep_removes_a_real_orphaned_worktree_and_prunes_metadata(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo = _init_repo(repo_root)

    sandbox_parent = tmp_path / "sandboxes"
    sandbox_parent.mkdir()
    temp_dir = sandbox_parent / "mensura-verification-crashed"
    temp_dir.mkdir()
    worktree_path = temp_dir / "worktree"
    repo.git.worktree("add", "--detach", str(worktree_path), "HEAD")

    # A crash leaves both the temp dir and the Git worktree metadata behind.
    assert worktree_path.exists()
    assert len(repo.git.worktree("list").splitlines()) == 2

    sweeper = VerificationSandboxSweeper(parent_dir=sandbox_parent)  # real git pruner
    summary = sweeper.sweep([str(repo_root)])

    assert summary.removed == 1
    assert summary.worktrees_pruned == 1
    assert not temp_dir.exists()
    # Git no longer lists the stale worktree, and its metadata directory is gone.
    assert len(repo.git.worktree("list").splitlines()) == 1
    assert not (repo_root / ".git" / "worktrees" / "worktree").exists()

    # Running again is safe: nothing left to remove, prune is a no-op.
    again = sweeper.sweep([str(repo_root)])
    assert (again.removed, again.skipped) == (0, 0)
