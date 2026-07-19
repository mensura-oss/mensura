import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient


def create_workspace(client: TestClient, root_path: Path) -> dict:
    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Context workspace", "rootPath": str(root_path)},
    )
    assert response.status_code == 201
    return response.json()


def build_inventory(client: TestClient, workspace_id: str) -> dict:
    response = client.post(f"/api/v1/workspaces/{workspace_id}/vault/inventory")
    assert response.status_code == 201
    return response.json()


def create_context_pack(client: TestClient, workspace_id: str, paths: list[str]):
    return client.post(
        f"/api/v1/workspaces/{workspace_id}/context-packs",
        json={"paths": paths},
    )


def context_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "context-repository"
    (repository / "assets").mkdir(parents=True)
    (repository / "notes").mkdir()
    (repository / "README.md").write_text("# Exact context\n", encoding="utf-8")
    (repository / "notes" / "large.txt").write_text("λ" * 10_000, encoding="utf-8")
    (repository / "assets" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\0binary")
    (repository / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    return repository


def test_context_pack_is_deterministic_immutable_and_retrievable(
    client: TestClient, tmp_path: Path
) -> None:
    repository = context_repository(tmp_path)
    workspace = create_workspace(client, repository)
    inventory = build_inventory(client, workspace["id"])

    first = create_context_pack(
        client,
        workspace["id"],
        ["README.md", "assets/logo.png"],
    )
    second = create_context_pack(
        client,
        workspace["id"],
        ["assets/logo.png", "README.md"],
    )

    assert first.status_code == 201
    assert first.headers["location"].endswith(first.json()["contextPack"]["id"])
    assert first.json()["created"] is True
    assert second.status_code == 201
    assert second.json()["created"] is False
    assert second.json()["contextPack"] == first.json()["contextPack"]

    manifest = first.json()["contextPack"]
    assert manifest["id"] == manifest["digest"]
    assert manifest["id"].startswith("sha256:")
    assert len(manifest["id"]) == 71
    assert manifest["workspaceId"] == workspace["id"]
    assert manifest["inventoryId"] == inventory["id"]
    assert manifest["schemaVersion"] == "1"
    assert [entry["path"] for entry in manifest["files"]] == [
        "assets/logo.png",
        "README.md",
    ]
    assert manifest["summary"] == {
        "fileCount": 2,
        "textFileCount": 1,
        "binaryFileCount": 1,
        "totalFileBytes": 31,
        "totalPreviewBytes": 16,
        "truncatedTextFileCount": 0,
    }

    binary, text = manifest["files"]
    assert binary["captureMode"] == "metadata_only"
    assert binary["previewText"] is None
    assert binary["encoding"] is None
    assert binary["previewBytes"] == 0
    assert binary["contentDigest"] == (
        f"sha256:{hashlib.sha256((repository / 'assets/logo.png').read_bytes()).hexdigest()}"
    )
    assert text["captureMode"] == "text_preview"
    assert text["previewText"] == "# Exact context\n"
    assert text["contentDigest"] == (
        f"sha256:{hashlib.sha256((repository / 'README.md').read_bytes()).hexdigest()}"
    )

    fetched = client.get(f"/api/v1/workspaces/{workspace['id']}/context-packs/{manifest['id']}")
    collection = client.get(f"/api/v1/workspaces/{workspace['id']}/context-packs")

    assert fetched.status_code == 200
    assert fetched.json() == manifest
    assert collection.status_code == 200
    assert collection.json()["total"] == 1
    assert collection.json()["items"] == [
        {key: value for key, value in manifest.items() if key not in {"limits", "files"}}
    ]


def test_context_pack_text_preview_is_utf8_bounded_and_reports_truncation(
    client: TestClient, tmp_path: Path
) -> None:
    repository = context_repository(tmp_path)
    workspace = create_workspace(client, repository)
    build_inventory(client, workspace["id"])

    response = create_context_pack(client, workspace["id"], ["notes/large.txt"])

    assert response.status_code == 201
    entry = response.json()["contextPack"]["files"][0]
    assert entry["previewBytes"] <= 16 * 1024
    assert len(entry["previewText"].encode("utf-8")) == entry["previewBytes"]
    assert entry["totalBytes"] == 20_000
    assert entry["truncated"] is True
    assert response.json()["contextPack"]["summary"]["truncatedTextFileCount"] == 1


def test_context_pack_rejects_invalid_excluded_duplicate_and_changed_files(
    client: TestClient, tmp_path: Path
) -> None:
    repository = context_repository(tmp_path)
    workspace = create_workspace(client, repository)
    build_inventory(client, workspace["id"])
    endpoint = f"/api/v1/workspaces/{workspace['id']}/context-packs"

    traversal = client.post(endpoint, json={"paths": ["../outside.txt"]})
    excluded = client.post(endpoint, json={"paths": [".env"]})
    missing = client.post(endpoint, json={"paths": ["missing.txt"]})
    duplicate = client.post(endpoint, json={"paths": ["README.md", "README.md"]})
    (repository / "README.md").write_text("changed size\n", encoding="utf-8")
    changed = client.post(endpoint, json={"paths": ["README.md"]})

    assert traversal.status_code == 422
    assert traversal.json()["type"] == "urn:mensura:problem:vault-path-invalid"
    assert excluded.status_code == 403
    assert excluded.json()["type"] == "urn:mensura:problem:vault-file-excluded"
    assert missing.status_code == 422
    assert missing.json()["type"] == "urn:mensura:problem:context-pack-invalid-selection"
    assert duplicate.status_code == 422
    assert duplicate.json()["type"] == "urn:mensura:problem:context-pack-invalid-selection"
    assert changed.status_code == 409
    assert changed.json()["type"] == "urn:mensura:problem:context-pack-file-changed"


def test_context_pack_returns_problems_for_missing_inventory_pack_and_large_selection(
    client: TestClient, tmp_path: Path
) -> None:
    repository = tmp_path / "many-files"
    repository.mkdir()
    for index in range(51):
        (repository / f"file-{index:02}.txt").write_text(str(index), encoding="utf-8")
    for index in range(17):
        (repository / f"large-{index:02}.txt").write_text("x" * 20_000, encoding="utf-8")
    workspace = create_workspace(client, repository)
    endpoint = f"/api/v1/workspaces/{workspace['id']}/context-packs"

    not_built = client.post(endpoint, json={"paths": ["file-00.txt"]})
    build_inventory(client, workspace["id"])
    too_large = client.post(
        endpoint,
        json={"paths": [f"file-{index:02}.txt" for index in range(51)]},
    )
    previews_too_large = client.post(
        endpoint,
        json={"paths": [f"large-{index:02}.txt" for index in range(17)]},
    )
    missing_pack = client.get(f"{endpoint}/sha256:{'0' * 64}")
    missing_workspace = client.get(f"/api/v1/workspaces/{uuid4()}/context-packs")

    assert not_built.status_code == 404
    assert not_built.json()["type"] == "urn:mensura:problem:vault-inventory-not-built"
    assert too_large.status_code == 413
    assert too_large.json()["type"] == "urn:mensura:problem:context-pack-too-large"
    assert previews_too_large.status_code == 413
    assert previews_too_large.json()["type"] == "urn:mensura:problem:context-pack-too-large"
    assert missing_pack.status_code == 404
    assert missing_pack.json()["type"] == "urn:mensura:problem:context-pack-not-found"
    assert missing_workspace.status_code == 404
    assert missing_workspace.json()["type"] == "urn:mensura:problem:resource-not-found"
