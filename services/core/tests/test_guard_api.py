import json
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient


def create_workspace(client: TestClient, root: Path) -> dict:
    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Guard workspace", "rootPath": str(root)},
    )
    assert response.status_code == 201
    return response.json()


def write_guard_config(
    root: Path,
    *,
    lint_command: list[str] | None = None,
    test_command: list[str] | None = None,
    lint_blocking: bool = True,
    test_blocking: bool = True,
) -> None:
    config_dir = root / ".mensura"
    config_dir.mkdir(parents=True)
    config = {
        "version": 1,
        "timeoutSeconds": 10,
        "checks": {
            "lint": {
                "command": lint_command
                or [sys.executable, "-m", "ruff", "check", "--output-format", "json", "."],
                "blocking": lint_blocking,
            },
            "test": {
                "command": test_command or [sys.executable, "-m", "pytest", "-q"],
                "blocking": test_blocking,
            },
        },
    }
    (config_dir / "guard.json").write_text(json.dumps(config))


def passing_workspace(tmp_path: Path) -> Path:
    root = tmp_path / "passing-workspace"
    root.mkdir()
    (root / "sample.py").write_text("VALUE = 1\n")
    (root / "test_sample.py").write_text("def test_value():\n    assert 1 + 1 == 2\n")
    write_guard_config(root)
    return root


def test_run_and_latest_return_structured_passing_results(
    client: TestClient, tmp_path: Path
) -> None:
    workspace = create_workspace(client, passing_workspace(tmp_path))

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/guard/runs",
        json={},
    )

    assert response.status_code == 201
    run = response.json()
    assert run["workspaceId"] == workspace["id"]
    assert run["status"] == "passed"
    assert run["blocking"] is False
    assert run["summary"] == {
        "totalCount": 2,
        "passedCount": 2,
        "failedCount": 0,
        "errorCount": 0,
        "blockingFailures": 0,
        "isBlocking": False,
    }
    assert [check["kind"] for check in run["checks"]] == ["lint", "test"]
    assert all(check["status"] == "passed" for check in run["checks"])
    assert all(check["durationMs"] >= 0 for check in run["checks"])
    assert all(len(check["stdout"].encode()) <= 8192 for check in run["checks"])
    assert client.get(f"/api/v1/workspaces/{workspace['id']}/guard/runs/latest").json() == run


def test_failed_lint_is_normalized_and_blocking(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "lint-failure"
    root.mkdir()
    (root / "broken.py").write_text("def broken(:\n")
    write_guard_config(root)
    workspace = create_workspace(client, root)

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/guard/runs",
        json={"checks": ["lint"]},
    )

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "failed"
    assert run["blocking"] is True
    assert run["summary"]["blockingFailures"] == 1
    assert run["checks"][0]["status"] == "failed"
    assert run["checks"][0]["exitCode"] == 1
    assert "diagnostic" in run["checks"][0]["summary"]


def test_failed_test_is_structured_but_can_be_non_blocking(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "test-failure"
    root.mkdir()
    (root / "test_failure.py").write_text("def test_failure():\n    assert False\n")
    write_guard_config(root, test_blocking=False)
    workspace = create_workspace(client, root)

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/guard/runs",
        json={"checks": ["test"]},
    )

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "failed"
    assert run["blocking"] is False
    assert run["summary"]["failedCount"] == 1
    assert run["summary"]["blockingFailures"] == 0
    assert run["checks"][0]["kind"] == "test"
    assert run["checks"][0]["status"] == "failed"
    assert run["checks"][0]["exitCode"] == 1


def test_missing_config_and_workspace_use_problem_details(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "no-config"
    root.mkdir()
    workspace = create_workspace(client, root)

    missing_config = client.post(
        f"/api/v1/workspaces/{workspace['id']}/guard/runs",
        json={},
    )
    missing_workspace_id = uuid4()
    missing_workspace = client.post(
        f"/api/v1/workspaces/{missing_workspace_id}/guard/runs",
        json={},
    )

    assert missing_config.status_code == 404
    assert missing_config.headers["content-type"] == "application/problem+json"
    assert missing_config.json()["type"] == "urn:mensura:problem:guard-configuration-not-found"
    assert missing_workspace.status_code == 404
    assert missing_workspace.json()["type"] == "urn:mensura:problem:resource-not-found"


def test_latest_has_an_explicit_empty_history_problem(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "no-history"
    root.mkdir()
    workspace = create_workspace(client, root)

    response = client.get(f"/api/v1/workspaces/{workspace['id']}/guard/runs/latest")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "urn:mensura:problem:guard-run-not-found"


def test_invalid_tool_configuration_uses_problem_details(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "invalid-config"
    root.mkdir()
    write_guard_config(
        root,
        lint_command=[sys.executable, "-m", "pytest", "-q"],
    )
    workspace = create_workspace(client, root)

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/guard/runs",
        json={},
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "urn:mensura:problem:invalid-guard-configuration"


def test_process_start_failure_is_a_sanitized_problem(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "missing-executable"
    root.mkdir()
    missing_python = root / "missing" / "python"
    write_guard_config(
        root,
        lint_command=[str(missing_python), "-m", "ruff", "check", "."],
    )
    workspace = create_workspace(client, root)

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/guard/runs",
        json={"checks": ["lint"]},
    )

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "urn:mensura:problem:guard-execution-failed"
    assert str(missing_python) not in response.text


def test_missing_root_is_an_unsupported_workspace_problem(
    client: TestClient, tmp_path: Path
) -> None:
    workspace = create_workspace(client, tmp_path / "missing-root")

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/guard/runs",
        json={},
    )

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "urn:mensura:problem:unsupported-workspace-state"
