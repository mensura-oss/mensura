"""Shared workspace-relative path resolution that refuses escapes and symlinks."""

from pathlib import Path


def resolve_safe_target(root: Path, relative_path: str) -> Path | None:
    """Resolve ``relative_path`` under ``root`` or return ``None`` when unsafe.

    A target is refused when the path is absolute, contains a parent-directory
    (``..``) component, or crosses a symlinked component, so callers can never
    read or write outside the workspace/sandbox root even if an upstream layer
    failed to normalize the path.
    """
    pure = Path(relative_path)
    if pure.is_absolute():
        return None
    parts = pure.parts
    if not parts or ".." in parts:
        return None

    target = root
    for part in parts[:-1]:
        target = target / part
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            return None
    target = target / parts[-1]
    if target.is_symlink():
        return None
    return target
