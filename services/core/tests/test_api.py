from uuid import uuid4

from fastapi.testclient import TestClient

from mensura_core.main import create_app
from mensura_core.repositories import InMemoryCoreRepository


def create_workspace(client: TestClient, *, root_path: str = "/tmp/mensura-project") -> dict:
    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Mensura project", "rootPath": root_path},
    )
    assert response.status_code == 201
    return response.json()


def create_task(client: TestClient, workspace_id: str) -> dict:
    response = client.post(
        "/api/v1/tasks",
        json={
            "workspaceId": workspace_id,
            "title": "Implement a small contract",
            "description": "Keep the behavior explicit.",
            "assignedRole": "coder",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "mensura-core",
        "version": "0.1.0",
    }


def test_create_and_list_workspaces(client: TestClient) -> None:
    created_response = client.post(
        "/api/v1/workspaces",
        json={"name": "  Local project  ", "rootPath": "/work/mensura"},
    )

    assert created_response.status_code == 201
    created = created_response.json()
    assert created["name"] == "Local project"
    assert created["rootPath"] == "/work/mensura"
    assert "location" not in created_response.headers

    listed_response = client.get("/api/v1/workspaces")
    assert listed_response.status_code == 200
    assert listed_response.json() == {"items": [created], "total": 1}


def test_create_get_task_and_create_get_run(client: TestClient) -> None:
    workspace = create_workspace(client)

    task_response = client.post(
        "/api/v1/tasks",
        json={
            "workspaceId": workspace["id"],
            "title": "Build the Core contract",
            "assignedRole": "architect",
        },
    )
    assert task_response.status_code == 201
    task = task_response.json()
    assert task["status"] == "ready"
    assert task["description"] == ""
    assert task_response.headers["location"] == f"/api/v1/tasks/{task['id']}"
    assert client.get(f"/api/v1/tasks/{task['id']}").json() == task

    run_response = client.post(f"/api/v1/tasks/{task['id']}/runs")
    assert run_response.status_code == 201
    run = run_response.json()
    assert run["taskId"] == task["id"]
    assert run["status"] == "queued"
    assert run["startedAt"] is None
    assert run["finishedAt"] is None
    assert run_response.headers["location"] == f"/api/v1/runs/{run['id']}"
    assert client.get(f"/api/v1/runs/{run['id']}").json() == run


def test_unknown_task_uses_problem_details(client: TestClient) -> None:
    task_id = uuid4()
    response = client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "urn:mensura:problem:resource-not-found",
        "title": "Resource not found",
        "status": 404,
        "detail": f"Task '{task_id}' was not found.",
        "instance": f"/api/v1/tasks/{task_id}",
    }


def test_task_requires_an_existing_workspace(client: TestClient) -> None:
    workspace_id = uuid4()
    response = client.post(
        "/api/v1/tasks",
        json={"workspaceId": str(workspace_id), "title": "Orphan task"},
    )

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == f"Workspace '{workspace_id}' was not found."


def test_duplicate_workspace_root_is_a_conflict(client: TestClient) -> None:
    create_workspace(client, root_path="/work/same")
    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Duplicate", "rootPath": "/work/same"},
    )

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "urn:mensura:problem:resource-conflict"


def test_validation_errors_use_problem_details_and_pointers(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workspaces",
        json={"name": "", "rootPath": ""},
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    problem = response.json()
    assert problem["type"] == "urn:mensura:problem:validation-error"
    assert problem["status"] == 422
    assert {error["pointer"] for error in problem["errors"]} == {
        "#/body/name",
        "#/body/rootPath",
    }


def test_invalid_path_id_uses_the_same_validation_contract(client: TestClient) -> None:
    response = client.get("/api/v1/runs/not-a-uuid")

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["errors"][0]["pointer"] == "#/path/run_id"


def test_framework_404_is_also_problem_details(client: TestClient) -> None:
    response = client.get("/not-a-route")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Not Found",
        "instance": "/not-a-route",
    }


def test_unexpected_errors_are_generic_problem_details() -> None:
    class FailingRepository(InMemoryCoreRepository):
        def list_workspaces(self):
            raise RuntimeError("internal storage detail")

    with TestClient(
        create_app(FailingRepository()), raise_server_exceptions=False
    ) as failing_client:
        response = failing_client.get("/api/v1/workspaces")

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "The server could not complete the request.",
        "instance": "/api/v1/workspaces",
    }
    assert "internal storage detail" not in response.text
