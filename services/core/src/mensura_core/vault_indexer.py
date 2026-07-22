"""Local, dependency-free Vault indexing: walk → classify → chunk → embed.

Retrieval is honest about what it is: chunks and queries are embedded with a deterministic
*hashing vectorizer* (term frequency over unigrams + bigrams hashed with ``blake2b`` into a
fixed number of buckets, L2-normalized) and ranked by cosine similarity. This is a lexical
vector model, not neural/semantic embeddings — but it is fully offline, deterministic, and
sits behind the :class:`Embedder` protocol so a real embedding model can replace it without
touching the schema or the service.

The walk reuses the read-only inventory's exclusion rules, language map, and safety posture
(never follow symlinks, never leave the workspace root).
"""

import hashlib
import math
import os
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from mensura_core.exceptions import VaultRootInvalidError
from mensura_core.vault_index_models import VaultSkippedFile, VaultSkipReason, VaultSourceType
from mensura_core.vault_index_repositories import IndexedChunk, IndexedMemoryItem
from mensura_core.vault_inventory import (
    LANGUAGE_BY_EXTENSION,
    LANGUAGE_BY_NAME,
    VaultInventoryRules,
)

# Indexing size cap: smaller than the 5 MB inventory/preview cap and explicit. Files that
# pass the inventory exclusion rules but exceed this are skipped as ``too_large``.
MAX_INDEXED_FILE_BYTES = 1_000_000
CHUNK_MAX_CHARS = 1500
CODE_CHUNK_MAX_LINES = 80
MAX_CHUNKS_PER_FILE = 200
SKIPPED_SAMPLE_LIMIT = 100
CONTROL_CHAR_RATIO = 0.05

EMBEDDING_DIM = 512

DOC_EXTENSIONS = frozenset({".md", ".markdown", ".mdx", ".rst", ".txt", ".adoc", ".text"})
CONFIG_EXTENSIONS = frozenset(
    {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".properties"}
)
CONFIG_LANGUAGES = frozenset({"JSON", "YAML", "TOML"})
DOC_LANGUAGES = frozenset({"Markdown"})
CODE_LANGUAGES = frozenset(
    {
        "C",
        "C++",
        "CSS",
        "Dockerfile",
        "Go",
        "HTML",
        "Java",
        "JavaScript",
        "Kotlin",
        "Makefile",
        "Python",
        "Rust",
        "SCSS",
        "Shell",
        "SQL",
        "Swift",
        "TypeScript",
        "XML",
    }
)

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")

IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def content_digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def text_digest(text: str) -> str:
    return content_digest(text.encode("utf-8"))


def _bucket(token: str, dim: int) -> str:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return str(int.from_bytes(digest, "big") % dim)


class Embedder(Protocol):
    def embed(self, text: str) -> dict[str, float]: ...


class HashingEmbedder:
    """Deterministic term-frequency hashing vectorizer over unigrams + bigrams.

    Uses ``blake2b`` (not Python's per-process-salted ``hash()``) so vectors persisted in one
    process match those computed for a query in another — search survives restarts.
    """

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self._dim = dim

    def embed(self, text: str) -> dict[str, float]:
        tokens = tokenize(text)
        if not tokens:
            return {}
        counts: Counter[str] = Counter()
        for token in tokens:
            counts[_bucket(token, self._dim)] += 1.0
        for first, second in pairwise(tokens):
            counts[_bucket(f"{first}\x1f{second}", self._dim)] += 1.0
        norm = math.sqrt(sum(value * value for value in counts.values()))
        if norm == 0.0:
            return {}
        return {bucket: value / norm for bucket, value in counts.items()}


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    """Dot product of two L2-normalized sparse vectors (== cosine similarity)."""
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(bucket, 0.0) for bucket, weight in left.items())


def classify_source_type(
    name: str, extension: str | None, language: str | None
) -> VaultSourceType | None:
    if extension in DOC_EXTENSIONS or language in DOC_LANGUAGES:
        return VaultSourceType.DOC
    if extension in CONFIG_EXTENSIONS or language in CONFIG_LANGUAGES:
        return VaultSourceType.CONFIG
    if language in CODE_LANGUAGES:
        return VaultSourceType.CODE
    return None


def _append_trimmed(
    chunks: list[tuple[int, int, str]], buffer: list[str], buffer_start: int
) -> None:
    """Append ``buffer`` (lines ``buffer_start``..) as a chunk, trimming blank edges."""
    first: int | None = None
    last: int | None = None
    for offset, line in enumerate(buffer):
        if line.strip():
            if first is None:
                first = offset
            last = offset
    if first is None or last is None:
        return
    text = "\n".join(buffer[first : last + 1])
    chunks.append((buffer_start + first, buffer_start + last, text))


def chunk_document(
    lines: list[str], *, max_chars: int = CHUNK_MAX_CHARS
) -> list[tuple[int, int, str]]:
    """Split docs by markdown headings + blank-line paragraph boundaries, bounded by size."""
    chunks: list[tuple[int, int, str]] = []
    buffer: list[str] = []
    buffer_start = 1
    char_count = 0
    for lineno, line in enumerate(lines, start=1):
        if _HEADING_RE.match(line) and buffer:
            _append_trimmed(chunks, buffer, buffer_start)
            buffer, char_count = [], 0
        if not buffer:
            buffer_start = lineno
        buffer.append(line)
        char_count += len(line) + 1
        blank = not line.strip()
        if (char_count >= max_chars and blank) or char_count >= max_chars * 2:
            _append_trimmed(chunks, buffer, buffer_start)
            buffer, char_count = [], 0
    if buffer:
        _append_trimmed(chunks, buffer, buffer_start)
    return chunks


def chunk_code(
    lines: list[str],
    *,
    max_chars: int = CHUNK_MAX_CHARS,
    max_lines: int = CODE_CHUNK_MAX_LINES,
) -> list[tuple[int, int, str]]:
    """Split code/config into bounded fixed line windows (≤max_lines and ≤max_chars)."""
    chunks: list[tuple[int, int, str]] = []
    buffer: list[str] = []
    buffer_start = 1
    char_count = 0
    for lineno, line in enumerate(lines, start=1):
        if buffer and (char_count + len(line) + 1 > max_chars or len(buffer) >= max_lines):
            _append_trimmed(chunks, buffer, buffer_start)
            buffer, char_count = [], 0
        if not buffer:
            buffer_start = lineno
        buffer.append(line)
        char_count += len(line) + 1
    if buffer:
        _append_trimmed(chunks, buffer, buffer_start)
    return chunks


def chunk_text(text: str, source_type: VaultSourceType) -> list[tuple[int, int, str]]:
    lines = text.split("\n")
    chunks = chunk_document(lines) if source_type is VaultSourceType.DOC else chunk_code(lines)
    return chunks[:MAX_CHUNKS_PER_FILE]


@dataclass(slots=True)
class BuiltVaultIndex:
    items: tuple[IndexedMemoryItem, ...]
    skipped_sample: tuple[VaultSkippedFile, ...]
    skipped_counts: dict[str, int] = field(default_factory=dict)
    excluded_entry_count: int = 0


class VaultIndexBuilder(Protocol):
    def build(
        self, workspace_root: str, *, workspace_id: UUID, index_id: UUID
    ) -> BuiltVaultIndex: ...


class LocalVaultIndexer:
    """Walk a workspace root and produce memory items + embedded chunks, deterministically."""

    def __init__(
        self,
        *,
        embedder: Embedder | None = None,
        rules: VaultInventoryRules | None = None,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
    ) -> None:
        self._embedder = embedder or HashingEmbedder()
        self._rules = rules or VaultInventoryRules()
        self._id_factory = id_factory
        self._clock = clock

    def build(self, workspace_root: str, *, workspace_id: UUID, index_id: UUID) -> BuiltVaultIndex:
        root = Path(workspace_root)
        try:
            resolved_root = root.resolve(strict=True)
        except OSError as error:
            raise VaultRootInvalidError(workspace_root) from error
        if not resolved_root.is_dir():
            raise VaultRootInvalidError(workspace_root)

        items: list[IndexedMemoryItem] = []
        skipped_sample: list[VaultSkippedFile] = []
        skipped_counts: dict[str, int] = {}
        excluded = self._walk(
            resolved_root,
            resolved_root,
            workspace_id,
            index_id,
            items,
            skipped_sample,
            skipped_counts,
        )
        items.sort(key=lambda item: (item.path.casefold(), item.path))
        return BuiltVaultIndex(
            items=tuple(items),
            skipped_sample=tuple(skipped_sample),
            skipped_counts=skipped_counts,
            excluded_entry_count=excluded,
        )

    def _record_skip(
        self,
        relative_path: str,
        reason: VaultSkipReason,
        sample: list[VaultSkippedFile],
        counts: dict[str, int],
    ) -> None:
        counts[reason.value] = counts.get(reason.value, 0) + 1
        if len(sample) < SKIPPED_SAMPLE_LIMIT:
            sample.append(VaultSkippedFile(path=relative_path, reason=reason))

    def _walk(
        self,
        root: Path,
        directory: Path,
        workspace_id: UUID,
        index_id: UUID,
        items: list[IndexedMemoryItem],
        skipped_sample: list[VaultSkippedFile],
        skipped_counts: dict[str, int],
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
                    relative_directory = path.relative_to(root)
                    if self._rules.excludes_directory(
                        entry.name
                    ) or self._rules.excludes_directory_path(relative_directory):
                        excluded += 1
                    else:
                        excluded += self._walk(
                            root,
                            path,
                            workspace_id,
                            index_id,
                            items,
                            skipped_sample,
                            skipped_counts,
                        )
                elif entry.is_file(follow_symlinks=False):
                    stat = entry.stat(follow_symlinks=False)
                    relative_path = path.relative_to(root).as_posix()
                    if self._rules.excludes_file(Path(relative_path), stat.st_size):
                        excluded += 1
                        continue
                    self._index_file(
                        path,
                        relative_path,
                        stat.st_size,
                        workspace_id,
                        index_id,
                        items,
                        skipped_sample,
                        skipped_counts,
                    )
                else:
                    excluded += 1
            except OSError:
                excluded += 1
        return excluded

    def _index_file(
        self,
        path: Path,
        relative_path: str,
        size_bytes: int,
        workspace_id: UUID,
        index_id: UUID,
        items: list[IndexedMemoryItem],
        skipped_sample: list[VaultSkippedFile],
        skipped_counts: dict[str, int],
    ) -> None:
        extension = path.suffix.casefold() or None
        language = LANGUAGE_BY_NAME.get(path.name.casefold()) or (
            LANGUAGE_BY_EXTENSION.get(extension) if extension else None
        )
        source_type = classify_source_type(path.name, extension, language)
        if source_type is None:
            self._record_skip(
                relative_path, VaultSkipReason.UNSUPPORTED_TYPE, skipped_sample, skipped_counts
            )
            return
        if size_bytes > MAX_INDEXED_FILE_BYTES:
            self._record_skip(
                relative_path, VaultSkipReason.TOO_LARGE, skipped_sample, skipped_counts
            )
            return
        try:
            data = path.read_bytes()
        except OSError:
            self._record_skip(
                relative_path, VaultSkipReason.READ_ERROR, skipped_sample, skipped_counts
            )
            return
        if b"\0" in data:
            self._record_skip(relative_path, VaultSkipReason.BINARY, skipped_sample, skipped_counts)
            return
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            self._record_skip(relative_path, VaultSkipReason.BINARY, skipped_sample, skipped_counts)
            return
        if text and _is_binary_text(text):
            self._record_skip(relative_path, VaultSkipReason.BINARY, skipped_sample, skipped_counts)
            return

        ranges = chunk_text(text, source_type)
        if not ranges:
            self._record_skip(relative_path, VaultSkipReason.EMPTY, skipped_sample, skipped_counts)
            return

        item_id = self._id_factory()
        indexed_at = self._clock()
        chunks = tuple(
            IndexedChunk(
                id=self._id_factory(),
                memory_item_id=item_id,
                chunk_index=chunk_index,
                start_line=start_line,
                end_line=end_line,
                char_count=len(chunk_body),
                digest=text_digest(chunk_body),
                text=chunk_body,
                embedding=self._embedder.embed(chunk_body),
            )
            for chunk_index, (start_line, end_line, chunk_body) in enumerate(ranges)
        )
        items.append(
            IndexedMemoryItem(
                id=item_id,
                workspace_id=workspace_id,
                index_id=index_id,
                path=relative_path,
                source_type=source_type,
                language=language,
                digest=content_digest(data),
                size_bytes=size_bytes,
                indexed_at=indexed_at,
                chunks=chunks,
            )
        )


def _is_binary_text(text: str) -> bool:
    controls = sum(character < " " and character not in "\b\t\n\f\r" for character in text[:8192])
    return controls / min(len(text), 8192) > CONTROL_CHAR_RATIO
