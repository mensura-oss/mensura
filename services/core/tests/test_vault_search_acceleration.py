"""Sub-linear Vault search: sparse inverted-index candidate retrieval + exact rerank.

These prove the acceleration is (a) *exact* — accelerated results equal the linear scan on the
same data — and (b) *safe* — dense/legacy indexes, over-broad queries, and a corrupt acceleration
index all fall back to the exact linear scan without wrong or silently-degraded scoring. Vectors
are deterministic (hand-built buckets or the offline lexical embedder), so nothing depends on a
running daemon.
"""

import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from vault_fakes import FakeSemanticEmbedder

from mensura_core.models import Workspace
from mensura_core.persistence.database import (
    create_persistence_engine,
    create_session_factory,
    run_migrations,
)
from mensura_core.persistence.repositories.core import SqlCoreRepository
from mensura_core.persistence.repositories.vault_index import SqlVaultIndexRepository
from mensura_core.repositories import InMemoryCoreRepository
from mensura_core.vault_embedding import HashingEmbedder
from mensura_core.vault_index_models import (
    VaultEmbeddingInfo,
    VaultIndexSnapshot,
    VaultIndexSummary,
    VaultSearchResponse,
    VaultSourceType,
)
from mensura_core.vault_index_repositories import (
    ChunkVector,
    IndexedChunk,
    IndexedMemoryItem,
    InMemoryVaultIndexRepository,
    VaultIndexRecord,
    VaultIndexRepository,
    index_is_acceleration_eligible,
    iter_chunk_postings,
)
from mensura_core.vault_index_service import VaultIndexService
from mensura_core.vault_indexer import LocalVaultIndexer

BASE = datetime(2026, 1, 1, tzinfo=UTC)
DIGEST = "sha256:" + "0" * 64


# --------------------------------------------------------------------------- fixtures / builders


def _summary(*, semantic: bool) -> VaultIndexSummary:
    return VaultIndexSummary(
        memory_item_count=0,
        chunk_count=0,
        code_file_count=0,
        doc_file_count=0,
        config_file_count=0,
        total_size_bytes=0,
        skipped_count=0,
        skipped_by_reason=[],
        languages=[],
        skipped_sample=[],
        embedding=VaultEmbeddingInfo(
            backend="ollama" if semantic else "hashing",
            model="fake",
            dim=3,
            semantic=semantic,
        ),
    )


def _record(
    workspace_id: UUID,
    files: list[tuple[str, VaultSourceType, list[tuple[dict[str, float], str]]]],
    *,
    semantic: bool = False,
    embedding: VaultEmbeddingInfo | None | object = ...,
) -> VaultIndexRecord:
    """Build an index record with fully-specified chunk embeddings (buckets under test control)."""
    index_id = uuid4()
    items: list[IndexedMemoryItem] = []
    for path, source_type, chunk_specs in files:
        item_id = uuid4()
        chunks = tuple(
            IndexedChunk(
                id=uuid4(),
                memory_item_id=item_id,
                chunk_index=index,
                start_line=1,
                end_line=1,
                char_count=len(text),
                digest=DIGEST,
                text=text,
                embedding=vector,
            )
            for index, (vector, text) in enumerate(chunk_specs)
        )
        items.append(
            IndexedMemoryItem(
                id=item_id,
                workspace_id=workspace_id,
                index_id=index_id,
                path=path,
                source_type=source_type,
                language=None,
                digest=DIGEST,
                size_bytes=100,
                indexed_at=BASE,
                chunks=chunks,
            )
        )
    summary = _summary(semantic=semantic)
    if embedding is not ...:
        summary = summary.model_copy(update={"embedding": embedding})
    snapshot = VaultIndexSnapshot(
        id=index_id, workspace_id=workspace_id, indexed_at=BASE, summary=summary
    )
    return VaultIndexRecord(snapshot=snapshot, items=tuple(items))


def _make_repo(root: Path) -> None:
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "src" / "auth.py").write_text(
        "def authenticate(username, password):\n"
        "    '''Verify a username and password pair.'''\n"
        "    return check_credentials(username, password)\n",
        encoding="utf-8",
    )
    (root / "src" / "render.py").write_text(
        "def render(canvas):\n    canvas.draw_pixels()\n", encoding="utf-8"
    )
    (root / "docs" / "auth.md").write_text(
        "# Authentication\n\nHow login and password verification works.\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")


def _service(
    root: Path,
    repository: VaultIndexRepository,
    core: InMemoryCoreRepository,
    *,
    embedder: object | None = None,
) -> tuple[VaultIndexService, UUID]:
    workspace = Workspace(
        id=uuid4(), name="demo", root_path=str(root), created_at=BASE, updated_at=BASE
    )
    core.add_workspace(workspace)
    indexer = LocalVaultIndexer(embedder=embedder) if embedder is not None else LocalVaultIndexer()
    service = VaultIndexService(
        core, indexer, repository, embedder=embedder, clock=lambda: BASE
    )
    return service, workspace.id


def _response_key(response: VaultSearchResponse) -> tuple:
    return (
        response.strategy,
        response.total,
        response.returned,
        [(hit.path, str(hit.chunk_id), hit.score, hit.chunk_index, hit.snippet) for hit in
         response.hits],
    )


class _ForceLinearRepo:
    """Wraps a repository but disables acceleration, so search runs the exact linear scan."""

    def __init__(self, inner: VaultIndexRepository) -> None:
        self._inner = inner

    def save_latest(self, record: VaultIndexRecord) -> None:
        self._inner.save_latest(record)

    def get_snapshot(self, workspace_id: UUID) -> VaultIndexSnapshot | None:
        return self._inner.get_snapshot(workspace_id)

    def list_item_summaries(self, workspace_id: UUID) -> tuple:
        return self._inner.list_item_summaries(workspace_id)

    def get_memory_item(self, memory_item_id: UUID) -> IndexedMemoryItem | None:
        return self._inner.get_memory_item(memory_item_id)

    def list_chunk_vectors(
        self, workspace_id: UUID, *, source_type: VaultSourceType | None = None
    ) -> list[ChunkVector]:
        return self._inner.list_chunk_vectors(workspace_id, source_type=source_type)

    def list_candidate_vectors(self, *args: object, **kwargs: object) -> None:
        return None


class _CorruptCandidateRepo(_ForceLinearRepo):
    """A corrupt acceleration index: candidate retrieval raises on every query."""

    def list_candidate_vectors(self, *args: object, **kwargs: object) -> list[ChunkVector] | None:
        raise RuntimeError("corrupt acceleration index")


# --------------------------------------------------------------------------- eligibility helpers


def test_eligibility_and_postings_only_for_the_sparse_lexical_space() -> None:
    workspace_id = uuid4()
    files = [("a.py", VaultSourceType.CODE, [({"1": 1.0}, "alpha")])]

    lexical = _record(workspace_id, files, semantic=False)
    assert index_is_acceleration_eligible(lexical.snapshot) is True
    assert [bucket for _, bucket in iter_chunk_postings(lexical)] == ["1"]

    semantic = _record(workspace_id, files, semantic=True)
    assert index_is_acceleration_eligible(semantic.snapshot) is False
    assert list(iter_chunk_postings(semantic)) == []  # dense → no postings

    legacy = _record(workspace_id, files, embedding=None)  # pre-cycle-27 index
    assert index_is_acceleration_eligible(legacy.snapshot) is False
    assert list(iter_chunk_postings(legacy)) == []


# --------------------------------------------------------------------------- candidate retrieval


def test_candidate_vectors_returns_only_chunks_sharing_a_query_bucket() -> None:
    workspace_id = uuid4()
    repo = InMemoryVaultIndexRepository()
    repo.save_latest(
        _record(
            workspace_id,
            [
                ("a.py", VaultSourceType.CODE, [({"1": 1.0}, "alpha")]),
                ("b.py", VaultSourceType.CODE, [({"2": 1.0}, "beta")]),
                ("c.py", VaultSourceType.CODE, [({"1": 0.5, "3": 0.5}, "alpha gamma")]),
            ],
        )
    )

    shared = repo.list_candidate_vectors(workspace_id, ["1"], candidate_limit=100)
    assert shared is not None
    assert {vector.path for vector in shared} == {"a.py", "c.py"}  # b.py shares no bucket
    # Sub-linear: fewer candidates than the full chunk set the linear scan would touch.
    assert len(shared) < len(repo.list_chunk_vectors(workspace_id))

    assert {v.path for v in repo.list_candidate_vectors(workspace_id, ["2"], candidate_limit=100)} \
        == {"b.py"}
    # A query bucket present on no chunk → accelerated *empty* result (not None → not a fallback).
    assert repo.list_candidate_vectors(workspace_id, ["9"], candidate_limit=100) == []


def test_candidate_vectors_apply_the_source_type_filter() -> None:
    workspace_id = uuid4()
    repo = InMemoryVaultIndexRepository()
    repo.save_latest(
        _record(
            workspace_id,
            [
                ("a.py", VaultSourceType.CODE, [({"1": 1.0}, "alpha")]),
                ("a.md", VaultSourceType.DOC, [({"1": 1.0}, "alpha")]),
            ],
        )
    )
    docs = repo.list_candidate_vectors(
        workspace_id, ["1"], source_type=VaultSourceType.DOC, candidate_limit=100
    )
    assert docs is not None
    assert {vector.path for vector in docs} == {"a.md"}


def test_candidate_vectors_none_for_dense_and_legacy_indexes() -> None:
    workspace_id = uuid4()
    files = [("a.py", VaultSourceType.CODE, [({"1": 1.0}, "alpha")])]

    dense_repo = InMemoryVaultIndexRepository()
    dense_repo.save_latest(_record(workspace_id, files, semantic=True))
    assert dense_repo.list_candidate_vectors(workspace_id, ["1"], candidate_limit=100) is None

    legacy_repo = InMemoryVaultIndexRepository()
    legacy_repo.save_latest(_record(workspace_id, files, embedding=None))
    assert legacy_repo.list_candidate_vectors(workspace_id, ["1"], candidate_limit=100) is None


def test_candidate_vectors_none_when_the_match_set_exceeds_the_cap() -> None:
    workspace_id = uuid4()
    repo = InMemoryVaultIndexRepository()
    repo.save_latest(
        _record(
            workspace_id,
            [(f"f{i}.py", VaultSourceType.CODE, [({"1": 1.0}, f"chunk {i}")]) for i in range(5)],
        )
    )
    # All five chunks share bucket "1"; a cap of 3 is a "too broad to accelerate" bounded fallback.
    assert repo.list_candidate_vectors(workspace_id, ["1"], candidate_limit=3) is None
    assert repo.list_candidate_vectors(workspace_id, ["1"], candidate_limit=5) is not None


def test_reindex_rebuilds_the_inverted_index_and_drops_stale_postings() -> None:
    workspace_id = uuid4()
    repo = InMemoryVaultIndexRepository()
    repo.save_latest(
        _record(workspace_id, [("a.py", VaultSourceType.CODE, [({"1": 1.0}, "alpha")])])
    )
    assert repo.list_candidate_vectors(workspace_id, ["1"], candidate_limit=100)  # bucket "1" hit

    # Re-index with a different bucket space; the stale "1" posting must be gone.
    repo.save_latest(
        _record(workspace_id, [("a.py", VaultSourceType.CODE, [({"2": 1.0}, "beta")])])
    )
    assert repo.list_candidate_vectors(workspace_id, ["1"], candidate_limit=100) == []
    assert {v.path for v in repo.list_candidate_vectors(workspace_id, ["2"], candidate_limit=100)} \
        == {"a.py"}


# --------------------------------------------------------------------------- service equivalence


ACCELERATED_QUERIES = [
    "authenticate password",
    "authentication login",
    "render canvas",
    "password",
    "verify credentials",
    "def return",  # common tokens → a broad candidate set, still exact
    "nonexistent zzzterm",  # no matches
]


def _index_pair(tmp_path: Path) -> tuple[VaultIndexService, VaultIndexService, UUID]:
    _make_repo(tmp_path)
    core = InMemoryCoreRepository()
    repo = InMemoryVaultIndexRepository()
    accelerated, workspace_id = _service(tmp_path, repo, core)
    accelerated.index_workspace(workspace_id)
    linear = VaultIndexService(
        core, LocalVaultIndexer(), _ForceLinearRepo(repo), embedder=HashingEmbedder(),
        clock=lambda: BASE,
    )
    return accelerated, linear, workspace_id


def test_accelerated_search_is_exactly_equivalent_to_the_linear_scan(tmp_path: Path) -> None:
    accelerated, linear, workspace_id = _index_pair(tmp_path)
    for query in ACCELERATED_QUERIES:
        accel = accelerated.search(workspace_id, query=query, limit=10, source_type=None)
        base = linear.search(workspace_id, query=query, limit=10, source_type=None)
        assert _response_key(accel) == _response_key(base), query


def test_accelerated_search_equivalence_holds_with_source_type_filter(tmp_path: Path) -> None:
    accelerated, linear, workspace_id = _index_pair(tmp_path)
    accel = accelerated.search(
        workspace_id, query="authentication login", limit=10, source_type=VaultSourceType.DOC
    )
    base = linear.search(
        workspace_id, query="authentication login", limit=10, source_type=VaultSourceType.DOC
    )
    assert _response_key(accel) == _response_key(base)
    assert accel.hits and all(hit.source_type is VaultSourceType.DOC for hit in accel.hits)


def test_accelerated_path_actually_prunes_for_a_selective_query(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    core = InMemoryCoreRepository()
    repo = InMemoryVaultIndexRepository()
    service, workspace_id = _service(tmp_path, repo, core)
    service.index_workspace(workspace_id)

    query_buckets = list(HashingEmbedder().embed("authenticate password"))
    candidates = repo.list_candidate_vectors(workspace_id, query_buckets, candidate_limit=100)
    assert candidates is not None
    # A selective query touches strictly fewer chunks than the whole index.
    assert 0 < len(candidates) < len(repo.list_chunk_vectors(workspace_id))


# --------------------------------------------------------------------------- fallback / safety


def test_corrupt_acceleration_index_falls_back_to_linear_scan(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _make_repo(tmp_path)
    core = InMemoryCoreRepository()
    repo = InMemoryVaultIndexRepository()
    builder, workspace_id = _service(tmp_path, repo, core)
    builder.index_workspace(workspace_id)

    corrupt = VaultIndexService(
        core, LocalVaultIndexer(), _CorruptCandidateRepo(repo), embedder=HashingEmbedder(),
        clock=lambda: BASE,
    )
    with caplog.at_level(logging.WARNING):
        response = corrupt.search(
            workspace_id, query="authenticate password", limit=5, source_type=None
        )
    # Correctness is preserved via the linear scan, and the degraded mode is logged (not hidden).
    assert response.hits and response.hits[0].path == "src/auth.py"
    assert "linear scan" in caplog.text


def test_semantic_index_returns_correct_results_via_linear_scan(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    core = InMemoryCoreRepository()
    repo = InMemoryVaultIndexRepository()
    service, workspace_id = _service(tmp_path, repo, core, embedder=FakeSemanticEmbedder())
    service.index_workspace(workspace_id)

    # Dense index → no postings persisted → the accelerated path declines (None).
    assert repo.list_candidate_vectors(workspace_id, ["0"], candidate_limit=100) is None
    # …but semantic search still works (linear scan), including the vocabulary-gap win.
    response = service.search(workspace_id, query="sign in", limit=5, source_type=None)
    assert response.strategy == "semantic-cosine:ollama/fake-semantic"
    assert response.total >= 1
    assert response.hits[0].path in {"src/auth.py", "docs/auth.md"}


# --------------------------------------------------------------------------- restart persistence


def _register_workspace(db_url: str, workspace_id: UUID) -> None:
    """Insert the workspace row so the index snapshot's workspace_id FK is satisfied."""
    engine = create_persistence_engine(db_url)
    SqlCoreRepository(create_session_factory(engine)).add_workspace(
        Workspace(
            id=workspace_id, name="accel", root_path=f"/tmp/{workspace_id}",
            created_at=BASE, updated_at=BASE,
        )
    )
    engine.dispose()


def test_postings_persist_and_accelerate_after_restart() -> None:
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="mensura_accel_")
    os.close(fd)
    db_url = f"sqlite:///{db_path}"
    workspace_id = uuid4()
    record = _record(
        workspace_id,
        [
            ("a.py", VaultSourceType.CODE, [({"1": 1.0}, "alpha")]),
            ("b.py", VaultSourceType.CODE, [({"2": 1.0}, "beta")]),
            ("c.py", VaultSourceType.CODE, [({"1": 0.5, "3": 0.5}, "alpha gamma")]),
        ],
    )
    try:
        run_migrations(db_url)
        _register_workspace(db_url, workspace_id)

        engine = create_persistence_engine(db_url)
        SqlVaultIndexRepository(create_session_factory(engine)).save_latest(record)
        engine.dispose()

        # Simulated restart: a brand-new engine/session factory over the same file.
        engine2 = create_persistence_engine(db_url)
        repo = SqlVaultIndexRepository(create_session_factory(engine2))
        candidates = repo.list_candidate_vectors(workspace_id, ["1"], candidate_limit=100)
        assert candidates is not None
        assert {vector.path for vector in candidates} == {"a.py", "c.py"}
        assert len(candidates) < len(repo.list_chunk_vectors(workspace_id))
        engine2.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_reindex_replaces_postings_in_sql() -> None:
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="mensura_accel_")
    os.close(fd)
    db_url = f"sqlite:///{db_path}"
    workspace_id = uuid4()
    try:
        run_migrations(db_url)
        _register_workspace(db_url, workspace_id)
        engine = create_persistence_engine(db_url)
        repo = SqlVaultIndexRepository(create_session_factory(engine))

        repo.save_latest(
            _record(workspace_id, [("a.py", VaultSourceType.CODE, [({"1": 1.0}, "alpha")])])
        )
        repo.save_latest(
            _record(workspace_id, [("a.py", VaultSourceType.CODE, [({"2": 1.0}, "beta")])])
        )
        # The stale "1" posting is gone; only the fresh "2" posting answers.
        assert repo.list_candidate_vectors(workspace_id, ["1"], candidate_limit=100) == []
        assert {
            v.path
            for v in repo.list_candidate_vectors(workspace_id, ["2"], candidate_limit=100)
        } == {"a.py"}
        engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)
