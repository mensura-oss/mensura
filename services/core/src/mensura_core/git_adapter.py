from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar, Protocol

from git import Repo
from git.diff import Diff
from git.exc import BadName, GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from mensura_core.exceptions import (
    NotGitRepositoryError,
    RepositoryPathNotFoundError,
    UnsupportedRepositoryStateError,
)
from mensura_core.repository_models import (
    RepositoryChangeType,
    RepositoryDiffMetadata,
    RepositoryInspection,
)


class GitRepositoryAdapter(Protocol):
    """Read-only inspection boundary for a workspace's local Git repository."""

    def inspect(self, path: str) -> RepositoryInspection: ...


class GitPythonRepositoryAdapter:
    """Inspect Git metadata without returning GitPython objects or patch content."""

    _CHANGE_TYPES: ClassVar[dict[str, RepositoryChangeType]] = {
        "A": RepositoryChangeType.ADDED,
        "C": RepositoryChangeType.COPIED,
        "D": RepositoryChangeType.DELETED,
        "M": RepositoryChangeType.MODIFIED,
        "R": RepositoryChangeType.RENAMED,
        "T": RepositoryChangeType.TYPE_CHANGED,
        "U": RepositoryChangeType.UNMERGED,
    }

    def inspect(self, path: str) -> RepositoryInspection:
        root = Path(path)
        if not root.exists() or not root.is_dir():
            raise RepositoryPathNotFoundError(path)

        try:
            repository = Repo(root, search_parent_directories=False)
        except NoSuchPathError as error:
            raise RepositoryPathNotFoundError(path) from error
        except InvalidGitRepositoryError as error:
            raise NotGitRepositoryError(path) from error

        if repository.bare:
            raise UnsupportedRepositoryStateError(path, "Bare repositories are not supported.")

        try:
            _ = repository.head.commit
        except (BadName, ValueError) as error:
            raise UnsupportedRepositoryStateError(
                path, "A repository without an initial commit is not supported."
            ) from error

        try:
            staged = self._metadata(
                repository.index.diff("HEAD", M=True), staged=True, repository_path=path
            )
            unstaged = self._metadata(
                repository.index.diff(None, M=True), staged=False, repository_path=path
            )
            untracked = [
                RepositoryDiffMetadata(
                    path=untracked_path,
                    change_type=RepositoryChangeType.UNTRACKED,
                    staged=False,
                )
                for untracked_path in repository.untracked_files
            ]
        except GitCommandError as error:
            raise UnsupportedRepositoryStateError(
                path, "Git could not inspect this repository state."
            ) from error

        staged_paths = {item.path for item in staged}
        unstaged_paths = {item.path for item in unstaged}
        untracked_paths = {item.path for item in untracked}
        metadata = sorted(
            [*staged, *unstaged, *untracked],
            key=lambda item: (item.path, not item.staged, item.change_type.value),
        )

        return RepositoryInspection(
            branch=None if repository.head.is_detached else repository.active_branch.name,
            is_dirty=bool(metadata),
            staged_count=len(staged_paths),
            unstaged_count=len(unstaged_paths),
            untracked_count=len(untracked_paths),
            changed_paths_count=len(staged_paths | unstaged_paths | untracked_paths),
            diff_metadata=metadata,
        )

    def _metadata(
        self,
        changes: Iterable[Diff],
        *,
        staged: bool,
        repository_path: str,
    ) -> list[RepositoryDiffMetadata]:
        metadata: list[RepositoryDiffMetadata] = []
        for change in changes:
            change_type = self._CHANGE_TYPES.get(change.change_type)
            if change_type is None:
                raise UnsupportedRepositoryStateError(
                    repository_path,
                    f"Git reported unsupported change type '{change.change_type}'.",
                )
            if change.change_type == "D" or staged:
                path = change.a_path or change.b_path
            else:
                path = change.b_path or change.a_path
            if path is None:
                raise UnsupportedRepositoryStateError(
                    repository_path,
                    "Git reported a changed entry without a path.",
                )
            old_path = None
            if change.change_type in {"C", "R"}:
                old_path = change.b_path if staged else change.a_path
            metadata.append(
                RepositoryDiffMetadata(
                    path=path,
                    change_type=change_type,
                    staged=staged,
                    old_path=old_path if old_path != path else None,
                )
            )
        return metadata
