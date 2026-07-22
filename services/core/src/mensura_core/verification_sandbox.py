"""Temporary isolated Git-worktree sandboxes for proposal verification."""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Protocol

from git import Repo
from git.exc import BadName, GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from mensura_core.exceptions import (
    NotGitRepositoryError,
    RepositoryPathNotFoundError,
    UnsupportedRepositoryStateError,
    VerificationSandboxError,
)

logger = logging.getLogger(__name__)

# Deterministic Mensura-ownership naming scheme. Every verification sandbox is a temp
# directory named ``mensura-verification-*`` containing exactly one ``worktree`` child.
# The startup sweep (verification_sweep.py) relies on this exact scheme to identify — and
# only ever delete — Mensura-owned sandboxes.
SANDBOX_TEMP_PREFIX = "mensura-verification-"
SANDBOX_WORKTREE_DIRNAME = "worktree"


def sandbox_parent_dir() -> Path:
    """Directory that holds verification sandboxes.

    Defaults to the system temp directory (the historical behavior). ``MENSURA_SANDBOX_DIR``
    overrides it with an explicit local path, which both the sandbox factory and the
    startup sweep honor so they always agree on where sandboxes live.
    """
    override = os.environ.get("MENSURA_SANDBOX_DIR")
    if override:
        return Path(override)
    return Path(tempfile.gettempdir())


class VerificationSandbox(Protocol):
    @property
    def path(self) -> Path: ...

    @property
    def commit_id(self) -> str: ...

    def cleanup(self) -> bool: ...


class VerificationSandboxFactory(Protocol):
    def create(self, workspace_root: str) -> VerificationSandbox: ...


class GitWorktreeSandbox:
    """One detached temporary worktree of the repository's current HEAD commit."""

    def __init__(self, repository: Repo, temp_dir: Path, worktree_path: Path) -> None:
        self._repository = repository
        self._temp_dir = temp_dir
        self._worktree_path = worktree_path
        self._commit_id = repository.head.commit.hexsha

    @property
    def path(self) -> Path:
        return self._worktree_path

    @property
    def commit_id(self) -> str:
        return self._commit_id

    def cleanup(self) -> bool:
        try:
            self._repository.git.worktree("remove", "--force", str(self._worktree_path))
        except GitCommandError:
            logger.warning("Temporary verification worktree could not be removed by Git.")
        shutil.rmtree(self._temp_dir, ignore_errors=True)
        try:
            self._repository.git.worktree("prune")
        except GitCommandError:
            logger.warning("Git worktree metadata could not be pruned after verification.")
        completed = not self._temp_dir.exists()
        if not completed:
            logger.warning("Temporary verification sandbox directory could not be deleted.")
        return completed


class GitWorktreeSandboxFactory:
    """Create isolated detached worktrees outside the repository path."""

    def create(self, workspace_root: str) -> VerificationSandbox:
        root = Path(workspace_root)
        if not root.exists() or not root.is_dir():
            raise RepositoryPathNotFoundError(workspace_root)

        try:
            repository = Repo(root, search_parent_directories=False)
        except NoSuchPathError as error:
            raise RepositoryPathNotFoundError(workspace_root) from error
        except InvalidGitRepositoryError as error:
            raise NotGitRepositoryError(workspace_root) from error

        if repository.bare:
            raise UnsupportedRepositoryStateError(
                workspace_root, "Bare repositories are not supported."
            )
        try:
            _ = repository.head.commit
        except (BadName, ValueError) as error:
            raise UnsupportedRepositoryStateError(
                workspace_root, "A repository without an initial commit is not supported."
            ) from error

        parent = sandbox_parent_dir()
        try:
            parent.mkdir(parents=True, exist_ok=True)
            temp_dir = Path(tempfile.mkdtemp(prefix=SANDBOX_TEMP_PREFIX, dir=parent))
        except OSError as error:
            raise VerificationSandboxError(
                "A temporary sandbox directory could not be created."
            ) from error

        worktree_path = temp_dir / SANDBOX_WORKTREE_DIRNAME
        try:
            repository.git.worktree("add", "--detach", str(worktree_path), "HEAD")
        except GitCommandError as error:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise VerificationSandboxError(
                "Git could not create a temporary verification worktree."
            ) from error
        return GitWorktreeSandbox(repository, temp_dir, worktree_path)
