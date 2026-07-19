import codecs
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from mensura_core.exceptions import VaultRootInvalidError
from mensura_core.vault_models import VaultFileInventoryItem, VaultFileKind

CLASSIFICATION_BYTES = 8 * 1024
MAX_INCLUDED_FILE_BYTES = 5 * 1024 * 1024

EXCLUDED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".cache",
        ".mypy_cache",
        ".next",
        ".pytest_cache",
        ".pnpm-store",
        ".ruff_cache",
        ".turbo",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "out",
        "output",
        "target",
        "venv",
    }
)

EXCLUDED_ARTIFACT_SUFFIXES = frozenset(
    {
        ".7z",
        ".a",
        ".bin",
        ".class",
        ".dmg",
        ".dll",
        ".dylib",
        ".exe",
        ".gz",
        ".iso",
        ".jar",
        ".lib",
        ".o",
        ".obj",
        ".pyo",
        ".pyc",
        ".rar",
        ".so",
        ".tar",
        ".wasm",
        ".whl",
        ".xz",
        ".zip",
    }
)

EXCLUDED_FILE_NAMES = frozenset({".ds_store", "thumbs.db"})

SENSITIVE_SUFFIXES = frozenset({".key", ".p12", ".pem", ".pfx"})
SENSITIVE_NAMES = frozenset(
    {
        "credentials",
        "credentials.json",
        "id_dsa",
        "id_ed25519",
        "id_rsa",
        ".netrc",
        ".npmrc",
        ".pypirc",
        "secrets.json",
    }
)

KNOWN_BINARY_SUFFIXES = frozenset(
    {
        ".avif",
        ".bmp",
        ".gif",
        ".ico",
        ".jpeg",
        ".jpg",
        ".mov",
        ".mp3",
        ".mp4",
        ".pdf",
        ".png",
        ".webp",
        ".woff",
        ".woff2",
    }
)

LANGUAGE_BY_EXTENSION = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".css": "CSS",
    ".go": "Go",
    ".h": "C",
    ".hpp": "C++",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".json": "JSON",
    ".kt": "Kotlin",
    ".md": "Markdown",
    ".py": "Python",
    ".rs": "Rust",
    ".scss": "SCSS",
    ".sh": "Shell",
    ".sql": "SQL",
    ".swift": "Swift",
    ".toml": "TOML",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".xml": "XML",
    ".yaml": "YAML",
    ".yml": "YAML",
}

LANGUAGE_BY_NAME = {
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
}


@dataclass(frozen=True, slots=True)
class BuiltVaultInventory:
    items: tuple[VaultFileInventoryItem, ...]
    excluded_entry_count: int


class VaultInventoryBuilder(Protocol):
    def build(self, workspace_root: str) -> BuiltVaultInventory: ...


class VaultInventoryRules:
    def excludes_directory(self, name: str) -> bool:
        return name.casefold() in EXCLUDED_DIRECTORY_NAMES

    def excludes_file(self, path: Path, size_bytes: int) -> bool:
        name = path.name.casefold()
        suffix = path.suffix.casefold()
        return (
            name == ".env"
            or name.startswith(".env.")
            or name in EXCLUDED_FILE_NAMES
            or name.startswith("secrets.")
            or name in SENSITIVE_NAMES
            or suffix in SENSITIVE_SUFFIXES
            or suffix in EXCLUDED_ARTIFACT_SUFFIXES
            or size_bytes > MAX_INCLUDED_FILE_BYTES
        )

    def excludes_relative_path(self, relative_path: str, *, size_bytes: int | None = None) -> bool:
        path = Path(relative_path)
        if any(self.excludes_directory(part) for part in path.parts[:-1]):
            return True
        return self.excludes_file(path, size_bytes or 0)


class LocalVaultInventoryBuilder:
    """Build deterministic metadata without following or mutating repository paths."""

    def __init__(self, rules: VaultInventoryRules | None = None) -> None:
        self._rules = rules or VaultInventoryRules()

    def build(self, workspace_root: str) -> BuiltVaultInventory:
        root = Path(workspace_root)
        try:
            resolved_root = root.resolve(strict=True)
        except OSError as error:
            raise VaultRootInvalidError(workspace_root) from error
        if not resolved_root.is_dir():
            raise VaultRootInvalidError(workspace_root)

        items: list[VaultFileInventoryItem] = []
        excluded_entry_count = self._walk(resolved_root, resolved_root, items)
        items.sort(key=lambda item: (item.path.casefold(), item.path))
        return BuiltVaultInventory(tuple(items), excluded_entry_count)

    def _walk(
        self,
        root: Path,
        directory: Path,
        items: list[VaultFileInventoryItem],
    ) -> int:
        try:
            entries = sorted(
                os.scandir(directory),
                key=lambda entry: (entry.name.casefold(), entry.name),
            )
        except OSError:
            return 1

        excluded = 0
        for entry in entries:
            path = Path(entry.path)
            try:
                if entry.is_symlink():
                    excluded += 1
                elif entry.is_dir(follow_symlinks=False):
                    if self._rules.excludes_directory(entry.name):
                        excluded += 1
                    else:
                        excluded += self._walk(root, path, items)
                elif entry.is_file(follow_symlinks=False):
                    stat = entry.stat(follow_symlinks=False)
                    relative_path = path.relative_to(root).as_posix()
                    if self._rules.excludes_file(Path(relative_path), stat.st_size):
                        excluded += 1
                        continue
                    kind = self._classify(path)
                    if kind is None:
                        excluded += 1
                        continue
                    extension = path.suffix.casefold() or None
                    items.append(
                        VaultFileInventoryItem(
                            path=relative_path,
                            name=path.name,
                            extension=extension,
                            language=self._language(path.name, extension),
                            kind=kind,
                            size_bytes=stat.st_size,
                        )
                    )
                else:
                    excluded += 1
            except OSError:
                excluded += 1
        return excluded

    def _classify(self, path: Path) -> VaultFileKind | None:
        if path.suffix.casefold() in KNOWN_BINARY_SUFFIXES:
            return VaultFileKind.BINARY
        try:
            with path.open("rb") as stream:
                sample = stream.read(CLASSIFICATION_BYTES)
        except OSError:
            return None
        if b"\0" in sample:
            return VaultFileKind.BINARY
        try:
            decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
            text = decoder.decode(sample, final=False)
        except UnicodeDecodeError:
            return VaultFileKind.BINARY
        if text:
            controls = sum(character < " " and character not in "\b\t\n\f\r" for character in text)
            if controls / len(text) > 0.05:
                return VaultFileKind.BINARY
        return VaultFileKind.TEXT

    def _language(self, name: str, extension: str | None) -> str | None:
        return LANGUAGE_BY_NAME.get(name.casefold()) or (
            LANGUAGE_BY_EXTENSION.get(extension) if extension else None
        )


def count_values(values: Sequence[str | None]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if value is not None:
            counts[value] = counts.get(value, 0) + 1
    return counts
