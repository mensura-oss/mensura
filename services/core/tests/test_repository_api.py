import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient


def git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def committed_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "api-repository"
    repository.mkdir()
    git(repository, "init")
    (repository / "tracked.txt").write_text("initial\n")
    git(repository, "add", "tracked.txt")
    git(
        repository,
        "-c",
        "commit.gpgsign=false",
        "-c",
        "user.name=Mensura Tests",
        "-c",
        "user.email=tests@mensura.local",
        "commit",
        "-m",
        "initial",
    )
    git(repository, "branch", "-M", "main")
    return repository


def create_workspace(client: TestClient, root_path: Path) -> dict:
    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Repository workspace", "rootPath": str(root_path)},
    )
    assert response.status_code == 201
    return response.json()


def test_repository_endpoint_returns_safe_dirty_metadata(
    client: TestClient, tmp_path: Path
) -> None:
    repository = committed_repository(tmp_path)
    (repository / "tracked.txt").write_text("changed\n")
    (repository / "untracked.txt").write_text("local\n")
    workspace = create_workspace(client, repository)

    response = client.get(f"/api/v1/workspaces/{workspace['id']}/repository")

    assert response.status_code == 200
    assert response.json() == {
        "workspaceId": workspace["id"],
        "isRepository": True,
        "branch": "main",
        "isDirty": True,
        "stagedCount": 0,
        "unstagedCount": 1,
        "untrackedCount": 1,
        "changedPathsCount": 2,
        "diffMetadata": [
            {
                "path": "tracked.txt",
                "changeType": "modified",
                "staged": False,
                "oldPath": None,
            },
            {
                "path": "untracked.txt",
                "changeType": "untracked",
                "staged": False,
                "oldPath": None,
            },
        ],
    }
    assert "patch" not in response.text.lower()
    assert "changed\\n" not in response.text


def test_repository_endpoint_preserves_a_null_detached_branch(
    client: TestClient, tmp_path: Path
) -> None:
    repository = committed_repository(tmp_path)
    git(repository, "checkout", "--detach", "HEAD")
    workspace = create_workspace(client, repository)

    response = client.get(f"/api/v1/workspaces/{workspace['id']}/repository")

    assert response.status_code == 200
    assert "branch" in response.json()
    assert response.json()["branch"] is None


def test_repository_endpoint_requires_an_existing_workspace(client: TestClient) -> None:
    workspace_id = uuid4()

    response = client.get(f"/api/v1/workspaces/{workspace_id}/repository")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "urn:mensura:problem:resource-not-found"


def test_repository_endpoint_rejects_a_missing_root(client: TestClient, tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"
    workspace = create_workspace(client, missing_root)

    response = client.get(f"/api/v1/workspaces/{workspace['id']}/repository")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "urn:mensura:problem:repository-path-not-found"


def test_repository_endpoint_rejects_a_non_repository(client: TestClient, tmp_path: Path) -> None:
    non_repository = tmp_path / "plain-directory"
    non_repository.mkdir()
    workspace = create_workspace(client, non_repository)

    response = client.get(f"/api/v1/workspaces/{workspace['id']}/repository")

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "urn:mensura:problem:not-a-git-repository"
