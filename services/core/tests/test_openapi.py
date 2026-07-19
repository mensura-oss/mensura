from fastapi.testclient import TestClient


def test_openapi_exposes_only_the_cycle_two_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert schema["info"]["version"] == "0.1.0"
    assert set(schema["paths"]) == {
        "/health",
        "/api/v1/workspaces",
        "/api/v1/tasks/{task_id}",
        "/api/v1/tasks",
        "/api/v1/tasks/{task_id}/runs",
        "/api/v1/runs/{run_id}",
    }


def test_openapi_documents_camel_case_and_problem_media_type(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    workspace_create = schema["components"]["schemas"]["WorkspaceCreate"]
    task = schema["components"]["schemas"]["Task"]

    assert set(workspace_create["properties"]) == {"name", "rootPath"}
    assert "workspaceId" in task["properties"]

    error_response = schema["paths"]["/api/v1/tasks/{task_id}"]["get"]["responses"]["404"]
    assert set(error_response["content"]) == {"application/problem+json"}
    assert error_response["content"]["application/problem+json"]["schema"]["title"] == (
        "ProblemDetails"
    )
