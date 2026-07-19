from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from mensura_core.vault_inventory import EXCLUDED_DIRECTORY_NAMES, MAX_INCLUDED_FILE_BYTES


def create_workspace(client: TestClient, root_path: Path) -> dict:
    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Vault workspace", "rootPath": str(root_path)},
    )
    assert response.status_code == 201
    return response.json()


def inventory_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "inventory-repository"
    (repository / "assets").mkdir(parents=True)
    (repository / "notes").mkdir()
    (repository / "src").mkdir()
    (repository / "README.md").write_text("# Inventory\n", encoding="utf-8")
    (repository / "assets" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\0binary")
    (repository / "notes" / "large.txt").write_text("x" * 20_000, encoding="utf-8")
    (repository / "src" / "alpha.ts").write_text("export {};\n", encoding="utf-8")
    (repository / "src" / "zeta.py").write_text("print('zeta')\n", encoding="utf-8")

    for directory_name in EXCLUDED_DIRECTORY_NAMES:
        excluded_directory = repository / directory_name
        excluded_directory.mkdir()
        (excluded_directory / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    (repository / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    (repository / ".DS_Store").write_bytes(b"finder metadata")
    (repository / "artifact.zip").write_bytes(b"archive")
    with (repository / "oversized.dat").open("wb") as stream:
        stream.truncate(MAX_INCLUDED_FILE_BYTES + 1)
    (repository / "linked.md").symlink_to(repository / "README.md")
    return repository


def build_inventory(client: TestClient, workspace_id: str):
    response = client.post(f"/api/v1/workspaces/{workspace_id}/vault/inventory")
    assert response.status_code == 201
    return response.json()


def test_vault_inventory_build_is_deterministic_and_summarized(
    client: TestClient, tmp_path: Path
) -> None:
    repository = inventory_repository(tmp_path)
    workspace = create_workspace(client, repository)

    inventory = build_inventory(client, workspace["id"])
    files_response = client.get(f"/api/v1/workspaces/{workspace['id']}/vault/files")

    assert inventory["status"] == "ready"
    assert inventory["workspaceId"] == workspace["id"]
    assert inventory["summary"] == {
        "includedFileCount": 5,
        "excludedEntryCount": len(EXCLUDED_DIRECTORY_NAMES) + 5,
        "textFileCount": 4,
        "binaryFileCount": 1,
        "totalSizeBytes": 20_000 + 12 + 15 + 11 + 14,
        "extensions": [
            {"value": ".md", "count": 1},
            {"value": ".png", "count": 1},
            {"value": ".py", "count": 1},
            {"value": ".ts", "count": 1},
            {"value": ".txt", "count": 1},
        ],
        "languages": [
            {"value": "Markdown", "count": 1},
            {"value": "Python", "count": 1},
            {"value": "TypeScript", "count": 1},
        ],
    }
    assert files_response.status_code == 200
    assert [item["path"] for item in files_response.json()["items"]] == [
        "assets/logo.png",
        "notes/large.txt",
        "README.md",
        "src/alpha.ts",
        "src/zeta.py",
    ]
    assert files_response.json()["inventoryId"] == inventory["id"]
    assert files_response.json()["total"] == 5
    assert files_response.json()["returned"] == 5


def test_vault_file_list_supports_path_extension_and_limit_filters(
    client: TestClient, tmp_path: Path
) -> None:
    repository = inventory_repository(tmp_path)
    workspace = create_workspace(client, repository)
    build_inventory(client, workspace["id"])

    query_response = client.get(
        f"/api/v1/workspaces/{workspace['id']}/vault/files",
        params={"query": "SRC/", "limit": 1},
    )
    extension_response = client.get(
        f"/api/v1/workspaces/{workspace['id']}/vault/files",
        params={"extension": "PY"},
    )

    assert query_response.status_code == 200
    assert query_response.json()["total"] == 2
    assert query_response.json()["returned"] == 1
    assert query_response.json()["items"][0]["path"] == "src/alpha.ts"
    assert [item["path"] for item in extension_response.json()["items"]] == ["src/zeta.py"]


def test_vault_text_preview_is_bounded_and_reports_truncation(
    client: TestClient, tmp_path: Path
) -> None:
    repository = inventory_repository(tmp_path)
    workspace = create_workspace(client, repository)
    inventory = build_inventory(client, workspace["id"])

    response = client.get(
        f"/api/v1/workspaces/{workspace['id']}/vault/files/content",
        params={"path": "notes/large.txt"},
    )

    assert response.status_code == 200
    preview = response.json()
    assert preview["inventoryId"] == inventory["id"]
    assert preview["file"]["path"] == "notes/large.txt"
    assert preview["encoding"] == "utf-8"
    assert preview["previewBytes"] == 16 * 1024
    assert len(preview["text"].encode()) == 16 * 1024
    assert preview["totalBytes"] == 20_000
    assert preview["truncated"] is True


def test_vault_preview_refuses_binary_excluded_and_traversing_paths(
    client: TestClient, tmp_path: Path
) -> None:
    repository = inventory_repository(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    workspace = create_workspace(client, repository)
    build_inventory(client, workspace["id"])
    endpoint = f"/api/v1/workspaces/{workspace['id']}/vault/files/content"

    binary = client.get(endpoint, params={"path": "assets/logo.png"})
    excluded = client.get(endpoint, params={"path": ".env"})
    symlink = client.get(endpoint, params={"path": "linked.md"})
    traversal = client.get(endpoint, params={"path": "../outside.txt"})
    absolute = client.get(endpoint, params={"path": str(outside)})

    assert binary.status_code == 415
    assert binary.headers["content-type"] == "application/problem+json"
    assert binary.json()["type"] == "urn:mensura:problem:vault-binary-preview-refused"
    assert excluded.status_code == 403
    assert excluded.json()["type"] == "urn:mensura:problem:vault-file-excluded"
    assert symlink.status_code == 403
    assert symlink.json()["type"] == "urn:mensura:problem:vault-file-excluded"
    assert traversal.status_code == 422
    assert traversal.json()["type"] == "urn:mensura:problem:vault-path-invalid"
    assert absolute.status_code == 422
    assert absolute.json()["type"] == "urn:mensura:problem:vault-path-invalid"


def test_vault_preview_rechecks_a_file_that_changed_after_inventory(
    client: TestClient, tmp_path: Path
) -> None:
    repository = inventory_repository(tmp_path)
    workspace = create_workspace(client, repository)
    build_inventory(client, workspace["id"])
    (repository / "README.md").write_bytes(b"\0now binary")

    response = client.get(
        f"/api/v1/workspaces/{workspace['id']}/vault/files/content",
        params={"path": "README.md"},
    )

    assert response.status_code == 415
    assert response.json()["type"] == "urn:mensura:problem:vault-binary-preview-refused"


def test_vault_inventory_refresh_replaces_the_latest_snapshot(
    client: TestClient, tmp_path: Path
) -> None:
    repository = inventory_repository(tmp_path)
    workspace = create_workspace(client, repository)
    first = build_inventory(client, workspace["id"])
    (repository / "new.toml").write_text("value = 1\n", encoding="utf-8")

    second = build_inventory(client, workspace["id"])
    latest = client.get(f"/api/v1/workspaces/{workspace['id']}/vault/inventory")

    assert second["id"] != first["id"]
    assert second["summary"]["includedFileCount"] == 6
    assert latest.status_code == 200
    assert latest.json() == second


def test_vault_returns_problems_for_missing_workspace_root_inventory_and_file(
    client: TestClient, tmp_path: Path
) -> None:
    missing_workspace = client.post(f"/api/v1/workspaces/{uuid4()}/vault/inventory")
    missing_root_workspace = create_workspace(client, tmp_path / "missing")
    missing_root = client.post(f"/api/v1/workspaces/{missing_root_workspace['id']}/vault/inventory")
    repository = inventory_repository(tmp_path)
    workspace = create_workspace(client, repository)
    not_built = client.get(f"/api/v1/workspaces/{workspace['id']}/vault/inventory")
    build_inventory(client, workspace["id"])
    missing_file = client.get(
        f"/api/v1/workspaces/{workspace['id']}/vault/files/content",
        params={"path": "missing.txt"},
    )

    assert missing_workspace.status_code == 404
    assert missing_workspace.json()["type"] == "urn:mensura:problem:resource-not-found"
    assert missing_root.status_code == 409
    assert missing_root.json()["type"] == "urn:mensura:problem:vault-root-invalid"
    assert not_built.status_code == 404
    assert not_built.json()["type"] == "urn:mensura:problem:vault-inventory-not-built"
    assert missing_file.status_code == 404
    assert missing_file.json()["type"] == "urn:mensura:problem:vault-file-not-found"
