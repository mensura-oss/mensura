from fastapi.testclient import TestClient


def test_openapi_exposes_the_implemented_v1_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert schema["info"]["version"] == "0.1.0"
    assert set(schema["paths"]) == {
        "/health",
        "/api/v1/workspaces",
        "/api/v1/workspaces/{workspace_id}/repository",
        "/api/v1/workspaces/{workspace_id}/guard/runs",
        "/api/v1/workspaces/{workspace_id}/guard/runs/latest",
        "/api/v1/workspaces/{workspace_id}/vault/inventory",
        "/api/v1/workspaces/{workspace_id}/vault/files",
        "/api/v1/workspaces/{workspace_id}/vault/files/content",
        "/api/v1/workspaces/{workspace_id}/context-packs",
        "/api/v1/workspaces/{workspace_id}/context-packs/{context_pack_id}",
        "/api/v1/tasks/{task_id}",
        "/api/v1/tasks",
        "/api/v1/tasks/{task_id}/runs",
        "/api/v1/runs/{run_id}",
        "/api/v1/runs/{run_id}/execute",
    }


def test_openapi_documents_camel_case_and_problem_media_type(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    workspace_create = schema["components"]["schemas"]["WorkspaceCreate"]
    task = schema["components"]["schemas"]["Task"]
    repository_summary = schema["components"]["schemas"]["RepositorySummary"]
    guard_run = schema["components"]["schemas"]["GuardRunResponse"]
    vault_inventory = schema["components"]["schemas"]["VaultInventorySnapshot"]
    vault_preview = schema["components"]["schemas"]["VaultFilePreview"]
    context_pack = schema["components"]["schemas"]["ContextPackManifest"]
    context_pack_create = schema["components"]["schemas"]["CreateContextPackRequest"]
    run_create = schema["components"]["schemas"]["RunCreate"]
    run = schema["components"]["schemas"]["Run"]
    run_execution = schema["components"]["schemas"]["RunExecution"]
    execution_result = schema["components"]["schemas"]["RunExecutionResult"]
    provider = schema["components"]["schemas"]["RunProviderMetadata"]

    assert set(workspace_create["properties"]) == {"name", "rootPath"}
    assert "workspaceId" in task["properties"]
    assert set(repository_summary["properties"]) == {
        "workspaceId",
        "isRepository",
        "branch",
        "isDirty",
        "stagedCount",
        "unstagedCount",
        "untrackedCount",
        "changedPathsCount",
        "diffMetadata",
    }
    assert all(
        forbidden not in repository_summary["properties"]
        for forbidden in ("patch", "content", "body", "hunks")
    )
    assert "workspaceId" in guard_run["properties"]
    assert "blocking" in guard_run["properties"]
    assert "checks" in guard_run["properties"]
    assert set(vault_inventory["properties"]) == {
        "id",
        "workspaceId",
        "status",
        "builtAt",
        "summary",
    }
    assert set(vault_preview["properties"]) == {
        "inventoryId",
        "workspaceId",
        "file",
        "encoding",
        "text",
        "previewBytes",
        "totalBytes",
        "truncated",
    }
    assert set(context_pack_create["properties"]) == {"paths"}
    assert set(run_create["properties"]) == {"contextPackId"}
    assert run_create["required"] == ["contextPackId"]
    assert set(run["properties"]) == {
        "id",
        "taskId",
        "contextPackId",
        "contextPack",
        "status",
        "execution",
        "startedAt",
        "finishedAt",
        "createdAt",
        "updatedAt",
    }
    assert set(run_execution["properties"]) == {
        "provider",
        "durationMs",
        "result",
        "failure",
    }
    assert set(execution_result["properties"]) == {
        "schemaVersion",
        "taskSummary",
        "interpretedIntent",
        "context",
        "warnings",
        "recommendedNextSteps",
    }
    assert set(provider["properties"]) == {
        "providerId",
        "adapterId",
        "adapterVersion",
        "model",
    }
    execute = schema["paths"]["/api/v1/runs/{run_id}/execute"]["post"]
    assert "requestBody" not in execute
    assert set(execute["responses"]) == {"200", "404", "409", "422", "502"}
    assert set(context_pack["properties"]) == {
        "id",
        "digest",
        "workspaceId",
        "inventoryId",
        "schemaVersion",
        "summary",
        "limits",
        "files",
    }

    error_response = schema["paths"]["/api/v1/tasks/{task_id}"]["get"]["responses"]["404"]
    assert set(error_response["content"]) == {"application/problem+json"}
    assert error_response["content"]["application/problem+json"]["schema"]["title"] == (
        "ProblemDetails"
    )
