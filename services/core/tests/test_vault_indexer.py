import os
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from uuid import UUID

import pytest

from mensura_core.exceptions import VaultRootInvalidError
from mensura_core.vault_index_models import VaultSkipReason, VaultSourceType
from mensura_core.vault_indexer import (
    MAX_INDEXED_FILE_BYTES,
    HashingEmbedder,
    LocalVaultIndexer,
    chunk_code,
    chunk_document,
    classify_source_type,
    content_digest,
    cosine_similarity,
    tokenize,
)

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _seq_ids():
    counter = {"n": 0}

    def factory() -> UUID:
        counter["n"] += 1
        return UUID(int=counter["n"])

    return factory


def _build(root: Path):
    indexer = LocalVaultIndexer(id_factory=_seq_ids(), clock=lambda: BASE)
    return indexer.build(str(root), workspace_id=UUID(int=1000), index_id=UUID(int=2000))


# ------------------------------------------------------------------ embedding


def test_embedding_is_deterministic_across_instances() -> None:
    text = "def authenticate(user, password): return verify(user, password)"
    assert HashingEmbedder().embed(text) == HashingEmbedder().embed(text)


def test_embedding_is_l2_normalized_and_self_similarity_is_one() -> None:
    vector = HashingEmbedder().embed("token store rotation policy")
    assert vector
    assert cosine_similarity(vector, vector) == pytest.approx(1.0)


def test_cosine_ranks_related_text_above_unrelated() -> None:
    embedder = HashingEmbedder()
    query = embedder.embed("authentication password login")
    related = embedder.embed("the login checks the password during authentication")
    unrelated = embedder.embed("rendering pixels to the canvas viewport")
    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


def test_empty_text_embeds_to_empty_vector() -> None:
    assert HashingEmbedder().embed("   \n\t ") == {}
    assert cosine_similarity({}, HashingEmbedder().embed("anything")) == 0.0


def test_tokenize_lowercases_and_splits_on_non_alphanumeric() -> None:
    assert tokenize("Hello, World_42!") == ["hello", "world_42"]


# ------------------------------------------------------------------ classification


@pytest.mark.parametrize(
    ("name", "extension", "language", "expected"),
    [
        ("main.py", ".py", "Python", VaultSourceType.CODE),
        ("app.tsx", ".tsx", "TypeScript", VaultSourceType.CODE),
        ("README.md", ".md", "Markdown", VaultSourceType.DOC),
        ("notes.txt", ".txt", None, VaultSourceType.DOC),
        ("pyproject.toml", ".toml", "TOML", VaultSourceType.CONFIG),
        ("config.json", ".json", "JSON", VaultSourceType.CONFIG),
        ("logo.png", ".png", None, None),
        ("LICENSE", None, None, None),
    ],
)
def test_classify_source_type(name, extension, language, expected) -> None:
    assert classify_source_type(name, extension, language) is expected


# ------------------------------------------------------------------ chunking


def test_chunk_document_splits_on_headings_and_keeps_line_ranges() -> None:
    text = "# Title\n\nIntro paragraph.\n\n## Section\n\nBody of the section.\n"
    chunks = chunk_document(text.split("\n"))
    assert [(start, end) for start, end, _ in chunks] == [(1, 3), (5, 7)]
    assert chunks[0][2].startswith("# Title")
    assert chunks[1][2].startswith("## Section")


def test_chunk_document_bounds_large_paragraphs_by_size() -> None:
    lines = [f"word{i} " * 5 for i in range(400)]
    chunks = chunk_document(lines, max_chars=200)
    # A non-blank run is split by the hard cap (max_chars * 2) with at most one line of
    # overflow, so every chunk stays comfortably bounded and the content is split.
    assert len(chunks) > 5
    assert all(len(text) < 3 * 200 for _, _, text in chunks)


def test_chunk_code_produces_bounded_line_windows() -> None:
    lines = [f"line_{i} = {i}" for i in range(1, 201)]
    chunks = chunk_code(lines, max_chars=10_000, max_lines=50)
    ranges = [(start, end) for start, end, _ in chunks]
    assert ranges == [(1, 50), (51, 100), (101, 150), (151, 200)]


def test_chunk_ranges_are_contiguous_and_one_based() -> None:
    lines = [f"row {i}" for i in range(1, 31)]
    chunks = chunk_code(lines, max_chars=10_000, max_lines=10)
    assert chunks[0][0] == 1
    for (_, prev_end, _), (next_start, _, _) in pairwise(chunks):
        assert next_start == prev_end + 1


# ------------------------------------------------------------------ walk / build


def _make_repo(root: Path) -> None:
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "node_modules" / "pkg").mkdir(parents=True)
    (root / "src" / "main.py").write_text(
        "def authenticate(user):\n    return True\n", encoding="utf-8"
    )
    (root / "docs" / "guide.md").write_text("# Guide\n\nHow to authenticate.\n", encoding="utf-8")
    (root / "config.json").write_text('{"name": "demo"}\n', encoding="utf-8")
    (root / "empty.py").write_text("", encoding="utf-8")
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01binary")
    (root / "data.bin").write_text("archive bytes", encoding="utf-8")  # excluded by suffix rule
    (root / "binary.py").write_bytes(b"x = 1\x00\x02 garbage")  # supported ext, binary content
    (root / "LICENSE").write_text("All rights reserved\n", encoding="utf-8")
    (root / "node_modules" / "pkg" / "index.js").write_text("export {};\n", encoding="utf-8")
    big = root / "huge.py"
    big.write_text("x = 1\n" + "# pad\n" * (MAX_INDEXED_FILE_BYTES // 6), encoding="utf-8")


def test_build_indexes_supported_files_with_metadata(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    built = _build(tmp_path)

    paths = {item.path: item for item in built.items}
    assert set(paths) == {"config.json", "docs/guide.md", "src/main.py"}

    main = paths["src/main.py"]
    assert main.source_type is VaultSourceType.CODE
    assert main.language == "Python"
    assert main.digest == content_digest((tmp_path / "src" / "main.py").read_bytes())
    assert main.workspace_id == UUID(int=1000)
    assert main.index_id == UUID(int=2000)
    assert main.indexed_at == BASE
    assert len(main.chunks) == 1

    chunk = main.chunks[0]
    assert chunk.memory_item_id == main.id
    assert chunk.start_line == 1
    assert chunk.chunk_index == 0
    assert chunk.char_count == len(chunk.text)
    assert chunk.embedding  # non-empty vector for code with tokens


def test_build_records_skip_reasons(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    built = _build(tmp_path)

    reasons = {skip.path: skip.reason for skip in built.skipped_sample}
    assert reasons["empty.py"] is VaultSkipReason.EMPTY
    assert reasons["logo.png"] is VaultSkipReason.UNSUPPORTED_TYPE
    assert reasons["LICENSE"] is VaultSkipReason.UNSUPPORTED_TYPE
    assert reasons["binary.py"] is VaultSkipReason.BINARY
    assert reasons["huge.py"] is VaultSkipReason.TOO_LARGE
    assert built.skipped_counts["too_large"] == 1
    assert "data.bin" not in reasons  # excluded by the inventory suffix rule, not a per-file skip


def test_build_excludes_ignored_directories(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    built = _build(tmp_path)
    assert all("node_modules" not in item.path for item in built.items)
    assert built.excluded_entry_count >= 1


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ on Windows")
def test_build_does_not_follow_symlinks(tmp_path: Path) -> None:
    (tmp_path / "real.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "link.py").symlink_to(tmp_path / "real.py")
    built = _build(tmp_path)
    assert {item.path for item in built.items} == {"real.py"}


def test_build_rejects_missing_root(tmp_path: Path) -> None:
    with pytest.raises(VaultRootInvalidError):
        _build(tmp_path / "does-not-exist")


def test_index_is_deterministic_across_runs(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    first = _build(tmp_path)
    second = _build(tmp_path)
    assert [item.path for item in first.items] == [item.path for item in second.items]
    assert [chunk.embedding for item in first.items for chunk in item.chunks] == [
        chunk.embedding for item in second.items for chunk in item.chunks
    ]
