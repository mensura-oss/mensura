"""Read-only access to a live workspace repository's current HEAD commit.

This never mutates the repository: it validates that the workspace is a usable
non-bare Git repository with an initial commit and returns the HEAD SHA for the
application audit record. No stage, commit, checkout, or worktree command runs.
"""

from pathlib import Path

from git import Repo
from git.exc import BadName, InvalidGitRepositoryError, NoSuchPathError

from mensura_core.exceptions import (
    NotGitRepositoryError,
    RepositoryPathNotFoundError,
    UnsupportedRepositoryStateError,
)


def resolve_live_head(root_path: str) -> str:
    root = Path(root_path)
    if not root.exists() or not root.is_dir():
        raise RepositoryPathNotFoundError(root_path)

    try:
        repository = Repo(root, search_parent_directories=False)
    except NoSuchPathError as error:
        raise RepositoryPathNotFoundError(root_path) from error
    except InvalidGitRepositoryError as error:
        raise NotGitRepositoryError(root_path) from error

    if repository.bare:
        raise UnsupportedRepositoryStateError(root_path, "Bare repositories are not supported.")
    try:
        return repository.head.commit.hexsha
    except (BadName, ValueError) as error:
        raise UnsupportedRepositoryStateError(
            root_path, "A repository without an initial commit is not supported."
        ) from error
