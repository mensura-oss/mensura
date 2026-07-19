import subprocess
from pathlib import Path

import pytest

from mensura_core.exceptions import (
    NotGitRepositoryError,
    RepositoryPathNotFoundError,
    UnsupportedRepositoryStateError,
)
from mensura_core.git_adapter import GitPythonRepositoryAdapter


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def committed_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init")
    (repository / "tracked.txt").write_text("initial\n")
    git(repository, "add", "tracked.txt")
    git(
        repository,
        "-c",
        "commit.gpgsign=false",
        "-c",
        "user.name=Mensura Tests",
        "-c",
        "user.email=tests@mensura.local",
        "commit",
        "-m",
        "initial",
    )
    git(repository, "branch", "-M", "main")
    return repository


def test_inspects_a_clean_repository_without_changing_it(tmp_path: Path) -> None:
    repository = committed_repository(tmp_path)
    before = git(repository, "status", "--porcelain=v1")

    summary = GitPythonRepositoryAdapter().inspect(str(repository))

    assert summary.branch == "main"
    assert summary.is_dirty is False
    assert summary.staged_count == 0
    assert summary.unstaged_count == 0
    assert summary.untracked_count == 0
    assert summary.changed_paths_count == 0
    assert summary.diff_metadata == []
    assert git(repository, "status", "--porcelain=v1") == before


def test_reports_staged_unstaged_and_untracked_metadata(tmp_path: Path) -> None:
    repository = committed_repository(tmp_path)
    (repository / "tracked.txt").write_text("staged\n")
    git(repository, "add", "tracked.txt")
    (repository / "tracked.txt").write_text("staged and unstaged\n")
    (repository / "untracked.txt").write_text("local\n")

    summary = GitPythonRepositoryAdapter().inspect(str(repository))

    assert summary.is_dirty is True
    assert summary.staged_count == 1
    assert summary.unstaged_count == 1
    assert summary.untracked_count == 1
    assert summary.changed_paths_count == 2
    assert [item.model_dump(by_alias=True) for item in summary.diff_metadata] == [
        {"path": "tracked.txt", "changeType": "modified", "staged": True, "oldPath": None},
        {"path": "tracked.txt", "changeType": "modified", "staged": False, "oldPath": None},
        {
            "path": "untracked.txt",
            "changeType": "untracked",
            "staged": False,
            "oldPath": None,
        },
    ]


def test_reports_a_staged_rename_without_patch_content(tmp_path: Path) -> None:
    repository = committed_repository(tmp_path)
    git(repository, "mv", "tracked.txt", "renamed.txt")

    summary = GitPythonRepositoryAdapter().inspect(str(repository))

    assert summary.staged_count == 1
    assert summary.changed_paths_count == 1
    assert summary.diff_metadata[0].change_type == "renamed"
    assert summary.diff_metadata[0].path == "renamed.txt"
    assert summary.diff_metadata[0].old_path == "tracked.txt"
    assert set(summary.diff_metadata[0].model_dump(by_alias=True)) == {
        "path",
        "changeType",
        "staged",
        "oldPath",
    }


def test_supports_detached_head_with_a_null_branch(tmp_path: Path) -> None:
    repository = committed_repository(tmp_path)
    git(repository, "checkout", "--detach", "HEAD")

    summary = GitPythonRepositoryAdapter().inspect(str(repository))

    assert summary.branch is None
    assert summary.is_dirty is False


def test_rejects_missing_and_non_repository_paths(tmp_path: Path) -> None:
    adapter = GitPythonRepositoryAdapter()
    non_repository = tmp_path / "not-a-repository"
    non_repository.mkdir()

    with pytest.raises(RepositoryPathNotFoundError):
        adapter.inspect(str(tmp_path / "missing"))
    with pytest.raises(NotGitRepositoryError):
        adapter.inspect(str(non_repository))


def test_rejects_a_repository_without_an_initial_commit(tmp_path: Path) -> None:
    repository = tmp_path / "empty-repository"
    repository.mkdir()
    git(repository, "init")

    with pytest.raises(UnsupportedRepositoryStateError):
        GitPythonRepositoryAdapter().inspect(str(repository))
