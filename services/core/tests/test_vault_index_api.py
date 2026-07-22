from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

RANDOM_UUID = "00000000-0000-0000-0000-000000000000"


def _make_repo(root: Path) -> None:
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "src" / "auth.py").write_text(
        "def authenticate(username, password):\n    return verify(username, password)\n",
        encoding="utf-8",
    )
    (root / "docs" / "guide.md").write_text(
        "# Guide\n\nHow authentication and login work here.\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")


def _workspace(client: TestClient, root: Path) -> str:
    response = client.post("/api/v1/workspaces", json={"name": "vault", "rootPath": str(root)})
    assert response.status_code == 201
    return response.json()["id"]


def _indexed_workspace(client: TestClient, tmp_path: Path) -> str:
    _make_repo(tmp_path)
    workspace_id = _workspace(client, tmp_path)
    indexed = client.post("/api/v1/vault/index", json={"workspaceId": workspace_id})
    assert indexed.status_code == 201
    return workspace_id


def test_index_endpoint_returns_snapshot(client: TestClient, tmp_path: Path) -> None:
    _make_repo(tmp_path)
    workspace_id = _workspace(client, tmp_path)

    response = client.post("/api/v1/vault/index", json={"workspaceId": workspace_id})

    assert response.status_code == 201
    body = response.json()
    assert body["workspaceId"] == workspace_id
    assert body["status"] == "ready"
    assert body["summary"]["memoryItemCount"] == 3
    assert body["summary"]["codeFileCount"] == 1
    assert body["summary"]["docFileCount"] == 1
    assert body["summary"]["configFileCount"] == 1


def test_index_unknown_workspace_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/vault/index", json={"workspaceId": RANDOM_UUID})
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


def test_get_index_before_indexing_returns_structured_404(
    client: TestClient, tmp_path: Path
) -> None:
    _make_repo(tmp_path)
    workspace_id = _workspace(client, tmp_path)

    response = client.get(f"/api/v1/vault/indexes/{workspace_id}")

    assert response.status_code == 404
    body = response.json()
    assert body["type"] == "urn:mensura:problem:vault-index-not-built"


def test_get_index_after_indexing_returns_snapshot(client: TestClient, tmp_path: Path) -> None:
    workspace_id = _indexed_workspace(client, tmp_path)
    response = client.get(f"/api/v1/vault/indexes/{workspace_id}")
    assert response.status_code == 200
    assert response.json()["workspaceId"] == workspace_id


def test_search_returns_ranked_hits(client: TestClient, tmp_path: Path) -> None:
    workspace_id = _indexed_workspace(client, tmp_path)

    response = client.post(
        "/api/v1/vault/search",
        json={"workspaceId": workspace_id, "query": "authenticate password", "limit": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "lexical-vector-cosine"
    assert body["hits"]
    assert body["hits"][0]["path"] == "src/auth.py"
    assert body["hits"][0]["score"] > 0


def test_search_filters_by_source_type(client: TestClient, tmp_path: Path) -> None:
    workspace_id = _indexed_workspace(client, tmp_path)

    response = client.post(
        "/api/v1/vault/search",
        json={
            "workspaceId": workspace_id,
            "query": "authentication login",
            "sourceType": "doc",
        },
    )

    assert response.status_code == 200
    assert all(hit["sourceType"] == "doc" for hit in response.json()["hits"])


def test_search_empty_query_is_rejected(client: TestClient, tmp_path: Path) -> None:
    workspace_id = _indexed_workspace(client, tmp_path)
    response = client.post(
        "/api/v1/vault/search", json={"workspaceId": workspace_id, "query": "   "}
    )
    assert response.status_code == 422


def test_search_before_indexing_returns_404(client: TestClient, tmp_path: Path) -> None:
    _make_repo(tmp_path)
    workspace_id = _workspace(client, tmp_path)
    response = client.post(
        "/api/v1/vault/search", json={"workspaceId": workspace_id, "query": "anything"}
    )
    assert response.status_code == 404
    assert response.json()["type"] == "urn:mensura:problem:vault-index-not-built"


def test_memory_endpoint_returns_item_and_chunks(client: TestClient, tmp_path: Path) -> None:
    workspace_id = _indexed_workspace(client, tmp_path)
    hit = client.post(
        "/api/v1/vault/search",
        json={"workspaceId": workspace_id, "query": "authenticate", "limit": 1},
    ).json()["hits"][0]

    response = client.get(f"/api/v1/vault/memory/{hit['memoryItemId']}")

    assert response.status_code == 200
    body = response.json()
    assert body["item"]["id"] == hit["memoryItemId"]
    assert body["item"]["path"] == "src/auth.py"
    assert len(body["chunks"]) == body["item"]["chunkCount"]


def test_memory_unknown_id_returns_structured_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/vault/memory/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["type"] == "urn:mensura:problem:vault-memory-not-found"


def test_summarize_returns_architecture_summary(client: TestClient, tmp_path: Path) -> None:
    workspace_id = _indexed_workspace(client, tmp_path)

    response = client.post("/api/v1/vault/summarize", json={"workspaceId": workspace_id})

    assert response.status_code == 200
    body = response.json()
    assert body["fileCount"] == 3
    assert {module["name"] for module in body["modules"]} >= {"src", "docs", "(root)"}
    assert "Python" in body["technologies"]
    assert "src/auth.py" not in body["entryPoints"]  # not an entry-point filename


def test_summarize_before_indexing_returns_404(client: TestClient, tmp_path: Path) -> None:
    _make_repo(tmp_path)
    workspace_id = _workspace(client, tmp_path)
    response = client.post("/api/v1/vault/summarize", json={"workspaceId": workspace_id})
    assert response.status_code == 404
