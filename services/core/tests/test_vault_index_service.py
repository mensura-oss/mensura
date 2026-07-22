from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from mensura_core.exceptions import (
    ResourceNotFoundError,
    VaultIndexNotBuiltError,
    VaultMemoryItemNotFoundError,
)
from mensura_core.models import Workspace
from mensura_core.repositories import InMemoryCoreRepository
from mensura_core.vault_index_models import VaultSourceType
from mensura_core.vault_index_repositories import InMemoryVaultIndexRepository
from mensura_core.vault_index_service import VaultIndexService
from mensura_core.vault_indexer import LocalVaultIndexer

BASE = datetime(2026, 1, 1, tzinfo=UTC)


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


def _service(root: Path) -> tuple[VaultIndexService, UUID]:
    core = InMemoryCoreRepository()
    workspace = Workspace(
        id=uuid4(),
        name="demo",
        root_path=str(root),
        created_at=BASE,
        updated_at=BASE,
    )
    core.add_workspace(workspace)
    service = VaultIndexService(
        core,
        LocalVaultIndexer(),
        InMemoryVaultIndexRepository(),
        clock=lambda: BASE,
    )
    return service, workspace.id


def test_index_workspace_summarizes_persisted_material(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    service, workspace_id = _service(tmp_path)

    snapshot = service.index_workspace(workspace_id)

    assert snapshot.workspace_id == workspace_id
    assert snapshot.indexed_at == BASE
    summary = snapshot.summary
    assert summary.memory_item_count == 4
    assert summary.code_file_count == 2
    assert summary.doc_file_count == 1
    assert summary.config_file_count == 1
    assert summary.chunk_count >= 4
    assert {count.value for count in summary.languages} == {"Python", "Markdown", "TOML"}


def test_get_index_requires_a_built_index(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    service, workspace_id = _service(tmp_path)
    with pytest.raises(VaultIndexNotBuiltError):
        service.get_index(workspace_id)
    service.index_workspace(workspace_id)
    assert service.get_index(workspace_id).workspace_id == workspace_id


def test_index_unknown_workspace_is_not_found(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    with pytest.raises(ResourceNotFoundError):
        service.index_workspace(uuid4())


def test_search_returns_relevant_chunks_ranked(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    service, workspace_id = _service(tmp_path)
    service.index_workspace(workspace_id)

    response = service.search(
        workspace_id, query="authenticate password", limit=5, source_type=None
    )

    assert response.total >= 1
    assert response.hits
    top = response.hits[0]
    assert top.path == "src/auth.py"
    assert top.score > 0
    assert "authenticate" in top.snippet
    # render.py shares no query terms and must not outrank auth material.
    assert all(hit.path != "src/render.py" for hit in response.hits[:1])


def test_search_can_filter_by_source_type(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    service, workspace_id = _service(tmp_path)
    service.index_workspace(workspace_id)

    docs_only = service.search(
        workspace_id, query="authentication login", limit=5, source_type=VaultSourceType.DOC
    )
    assert docs_only.hits
    assert all(hit.source_type is VaultSourceType.DOC for hit in docs_only.hits)


def test_search_with_no_matches_returns_empty(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    service, workspace_id = _service(tmp_path)
    service.index_workspace(workspace_id)

    response = service.search(
        workspace_id, query="quantumzzz nonexistentxyz", limit=5, source_type=None
    )
    assert response.total == 0
    assert response.hits == []


def test_search_requires_a_built_index(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    service, workspace_id = _service(tmp_path)
    with pytest.raises(VaultIndexNotBuiltError):
        service.search(workspace_id, query="anything", limit=5, source_type=None)


def test_get_memory_item_returns_item_and_chunks(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    service, workspace_id = _service(tmp_path)
    service.index_workspace(workspace_id)
    hit = service.search(workspace_id, query="authenticate", limit=1, source_type=None).hits[0]

    detail = service.get_memory_item(hit.memory_item_id)

    assert detail.item.id == hit.memory_item_id
    assert detail.item.path == "src/auth.py"
    assert detail.item.chunk_count == len(detail.chunks)
    assert detail.chunks[0].start_line == 1


def test_get_missing_memory_item_raises(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    with pytest.raises(VaultMemoryItemNotFoundError):
        service.get_memory_item(uuid4())


def test_summarize_reports_modules_and_technologies(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    service, workspace_id = _service(tmp_path)
    service.index_workspace(workspace_id)

    summary = service.summarize(workspace_id)

    assert summary.file_count == 4
    module_names = {module.name for module in summary.modules}
    assert {"src", "docs", "(root)"} <= module_names
    src_module = next(module for module in summary.modules if module.name == "src")
    assert src_module.file_count == 2
    assert src_module.primary_language == "Python"
    assert "Python" in summary.technologies


def test_summarize_requires_a_built_index(tmp_path: Path) -> None:
    service, workspace_id = _service(tmp_path)
    with pytest.raises(VaultIndexNotBuiltError):
        service.summarize(workspace_id)


def test_reindex_replaces_previous_index(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    service, workspace_id = _service(tmp_path)
    first = service.index_workspace(workspace_id)

    (tmp_path / "src" / "extra.py").write_text("def added():\n    return 1\n", encoding="utf-8")
    second = service.index_workspace(workspace_id)

    assert second.id != first.id
    assert second.summary.memory_item_count == first.summary.memory_item_count + 1
    # The stale index id is gone; only the latest snapshot answers.
    assert service.get_index(workspace_id).id == second.id
