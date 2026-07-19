from collections.abc import Sequence
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from mensura_core.context_pack_models import (
    ContextPackFileEntry,
    ContextPackFileSummary,
    ContextPackLimits,
    ContextPackManifest,
)
from mensura_core.main import create_app
from mensura_core.models import RunExecutionResult, RunStatus
from mensura_core.provider_adapter import (
    DeterministicReviewProvider,
    ProviderExecutionRequest,
)
from mensura_core.repositories import InMemoryCoreRepository


class FixtureContextPackRepository:
    def __init__(self) -> None:
        self.manifests: dict[tuple[UUID, str], ContextPackManifest] = {}

    def save_if_absent(self, manifest: ContextPackManifest) -> bool:
        key = (manifest.workspace_id, manifest.id)
        if key in self.manifests:
            return False
        self.manifests[key] = manifest
        return True

    def get(self, workspace_id: UUID, context_pack_id: str) -> ContextPackManifest | None:
        return self.manifests.get((workspace_id, context_pack_id))

    def find_by_id(self, context_pack_id: str) -> ContextPackManifest | None:
        return next(
            (
                manifest
                for (_, stored_id), manifest in self.manifests.items()
                if stored_id == context_pack_id
            ),
            None,
        )

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[ContextPackManifest]:
        return tuple(
            manifest
            for (stored_workspace_id, _), manifest in self.manifests.items()
            if stored_workspace_id == workspace_id
        )

    def remove(self, workspace_id: UUID, context_pack_id: str) -> None:
        self.manifests.pop((workspace_id, context_pack_id))


class ObservingProvider(DeterministicReviewProvider):
    def __init__(self, repository: InMemoryCoreRepository) -> None:
        self.repository = repository
        self.request: ProviderExecutionRequest | None = None

    def execute(self, request: ProviderExecutionRequest) -> RunExecutionResult:
        current = next(
            run for run in self.repository._runs.values() if run.task_id == request.task.id
        )
        assert current.status is RunStatus.RUNNING
        assert current.started_at is not None
        assert current.finished_at is None
        assert current.execution is not None
        assert current.execution.result is None
        self.request = request
        return super().execute(request)


class FailingProvider(DeterministicReviewProvider):
    def execute(self, request: ProviderExecutionRequest) -> RunExecutionResult:
        raise RuntimeError("provider secret must not escape")


class InvalidResultProvider(DeterministicReviewProvider):
    def execute(self, request: ProviderExecutionRequest) -> RunExecutionResult:
        return {"schemaVersion": "1"}  # type: ignore[return-value]


def create_manifest(workspace_id: UUID) -> ContextPackManifest:
    digest = f"sha256:{'c' * 64}"
    return ContextPackManifest(
        id=digest,
        digest=digest,
        workspace_id=workspace_id,
        inventory_id=uuid4(),
        summary=ContextPackFileSummary(
            file_count=1,
            text_file_count=1,
            binary_file_count=0,
            total_file_bytes=24,
            total_preview_bytes=24,
            truncated_text_file_count=0,
        ),
        limits=ContextPackLimits(
            max_files=50,
            max_preview_bytes_per_file=16_384,
            max_total_preview_bytes=262_144,
        ),
        files=(
            ContextPackFileEntry(
                path="src/example.py",
                name="example.py",
                extension=".py",
                language="Python",
                kind="text",
                size_bytes=24,
                content_digest=f"sha256:{'d' * 64}",
                capture_mode="text_preview",
                encoding="utf-8",
                preview_text="print('immutable input')",
                preview_bytes=24,
                total_bytes=24,
                truncated=False,
            ),
        ),
    )


def create_bound_run(
    client: TestClient, context_packs: FixtureContextPackRepository
) -> tuple[dict[str, object], ContextPackManifest]:
    workspace_response = client.post(
        "/api/v1/workspaces",
        json={"name": "Execution", "rootPath": "/not-used-by-provider"},
    )
    workspace = workspace_response.json()
    manifest = create_manifest(UUID(workspace["id"]))
    assert context_packs.save_if_absent(manifest)
    task = client.post(
        "/api/v1/tasks",
        json={
            "workspaceId": workspace["id"],
            "title": "Review immutable context",
            "description": "Summarize the selected evidence without changing files.",
        },
    ).json()
    run_response = client.post(
        f"/api/v1/tasks/{task['id']}/runs",
        json={"contextPackId": manifest.id},
    )
    assert run_response.status_code == 201
    return run_response.json(), manifest


def test_execute_queued_run_persists_explicit_transitions_and_result() -> None:
    repository = InMemoryCoreRepository()
    context_packs = FixtureContextPackRepository()
    provider = ObservingProvider(repository)
    with TestClient(
        create_app(
            repository=repository,
            context_pack_repository=context_packs,
            provider=provider,
        )
    ) as client:
        queued, manifest = create_bound_run(client, context_packs)

        response = client.post(f"/api/v1/runs/{queued['id']}/execute")

        assert response.status_code == 200
        run = response.json()
        assert run["status"] == "succeeded"
        assert run["startedAt"] is not None
        assert run["finishedAt"] is not None
        assert run["execution"]["provider"] == {
            "providerId": "mensura.builtin",
            "adapterId": "deterministic-review",
            "adapterVersion": "1.0.0",
            "model": None,
        }
        assert run["execution"]["durationMs"] >= 0
        assert run["execution"]["failure"] is None
        result = run["execution"]["result"]
        assert result["schemaVersion"] == "1"
        assert result["interpretedIntent"].startswith("Summarize")
        assert result["context"]["contextPackId"] == manifest.id
        assert result["context"]["languages"] == ["Python"]
        assert result["recommendedNextSteps"]
        assert provider.request is not None
        assert provider.request.context_pack == manifest
        serialized_request = provider.request.model_dump_json()
        assert "root_path" not in serialized_request
        assert "rootPath" not in serialized_request
        assert client.get(f"/api/v1/runs/{queued['id']}").json() == run


def test_execute_rejects_missing_run_and_terminal_run() -> None:
    context_packs = FixtureContextPackRepository()
    with TestClient(create_app(context_pack_repository=context_packs)) as client:
        missing_id = uuid4()
        missing = client.post(f"/api/v1/runs/{missing_id}/execute")
        queued, _ = create_bound_run(client, context_packs)
        assert client.post(f"/api/v1/runs/{queued['id']}/execute").status_code == 200
        repeated = client.post(f"/api/v1/runs/{queued['id']}/execute")

    assert missing.status_code == 404
    assert missing.json()["type"] == "urn:mensura:problem:resource-not-found"
    assert repeated.status_code == 409
    assert repeated.headers["content-type"] == "application/problem+json"
    assert repeated.json()["type"] == "urn:mensura:problem:run-invalid-state"


def test_execute_rejects_a_missing_bound_context_pack() -> None:
    context_packs = FixtureContextPackRepository()
    with TestClient(create_app(context_pack_repository=context_packs)) as client:
        queued, manifest = create_bound_run(client, context_packs)
        context_packs.remove(manifest.workspace_id, manifest.id)

        response = client.post(f"/api/v1/runs/{queued['id']}/execute")

        assert response.status_code == 409
        assert response.json()["type"] == "urn:mensura:problem:run-context-pack-missing"
        stored = client.get(f"/api/v1/runs/{queued['id']}").json()
        assert stored["status"] == "queued"
        assert stored["startedAt"] is None


def test_execute_rejects_inconsistent_workspace_ownership() -> None:
    repository = InMemoryCoreRepository()
    context_packs = FixtureContextPackRepository()
    with TestClient(
        create_app(repository=repository, context_pack_repository=context_packs)
    ) as client:
        queued, _ = create_bound_run(client, context_packs)
        stored = repository.get_run(UUID(queued["id"]))
        assert stored is not None
        inconsistent = stored.model_copy(
            update={
                "context_pack": stored.context_pack.model_copy(update={"workspace_id": uuid4()})
            }
        )
        assert repository.replace_run_if_status(inconsistent, RunStatus.QUEUED)

        response = client.post(f"/api/v1/runs/{queued['id']}/execute")

    assert response.status_code == 409
    assert response.json()["type"] == "urn:mensura:problem:run-context-inconsistent"


def test_provider_failure_persists_bounded_failed_run() -> None:
    context_packs = FixtureContextPackRepository()
    with TestClient(
        create_app(context_pack_repository=context_packs, provider=FailingProvider())
    ) as client:
        queued, _ = create_bound_run(client, context_packs)
        response = client.post(f"/api/v1/runs/{queued['id']}/execute")
        stored = client.get(f"/api/v1/runs/{queued['id']}").json()

    assert response.status_code == 502
    assert response.json()["type"] == "urn:mensura:problem:provider-execution-failed"
    assert "secret" not in response.text
    assert stored["status"] == "failed"
    assert stored["startedAt"] is not None
    assert stored["finishedAt"] is not None
    assert stored["execution"]["result"] is None
    assert stored["execution"]["failure"]["code"] == "provider_execution_failed"
    assert "secret" not in stored["execution"]["failure"]["summary"]


def test_invalid_provider_result_persists_structured_failure() -> None:
    context_packs = FixtureContextPackRepository()
    with TestClient(
        create_app(context_pack_repository=context_packs, provider=InvalidResultProvider())
    ) as client:
        queued, _ = create_bound_run(client, context_packs)
        response = client.post(f"/api/v1/runs/{queued['id']}/execute")
        stored = client.get(f"/api/v1/runs/{queued['id']}").json()

    assert response.status_code == 502
    assert response.json()["type"] == "urn:mensura:problem:structured-result-invalid"
    assert stored["status"] == "failed"
    assert stored["execution"]["failure"]["code"] == "structured_result_invalid"
