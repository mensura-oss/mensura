from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from mensura_core.models import (
    ChangeProposalChangeType,
    ChangeProposalDraft,
    ChangeProposalDraftFileChange,
    RunExecutionResult,
)
from mensura_core.provider_adapter import (
    DeterministicReviewProvider,
    ProviderExecutionRequest,
)


class ProposalProvider(DeterministicReviewProvider):
    def __init__(self, draft: ChangeProposalDraft) -> None:
        self._draft = draft

    def execute(self, request: ProviderExecutionRequest) -> RunExecutionResult:
        result = super().execute(request)
        return result.model_copy(update={"proposal_draft": self._draft})


def proposal_draft(
    *,
    path: str = "src/example.py",
    change_type: ChangeProposalChangeType = ChangeProposalChangeType.MODIFY,
    text: str | None = "print('proposed output')\n",
) -> ChangeProposalDraft:
    return ChangeProposalDraft(
        summary="Update the bounded example.",
        rationale="The immutable task and captured text identify this file as the change target.",
        file_changes=(
            ChangeProposalDraftFileChange(
                path=path,
                change_type=change_type,
                language="Python",
                proposed_text=text,
            ),
        ),
    )


def create_successful_run(client: TestClient, root: Path) -> tuple[dict, dict, str]:
    source = root / "src" / "example.py"
    source.parent.mkdir(parents=True)
    original = "print('immutable input')\n"
    source.write_text(original, encoding="utf-8")
    workspace = client.post(
        "/api/v1/workspaces",
        json={"name": "Proposal", "rootPath": str(root)},
    ).json()
    assert client.post(f"/api/v1/workspaces/{workspace['id']}/vault/inventory").status_code == 201
    pack_response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/context-packs",
        json={"paths": ["src/example.py"]},
    )
    assert pack_response.status_code == 201
    pack = pack_response.json()["contextPack"]
    task = client.post(
        "/api/v1/tasks",
        json={
            "workspaceId": workspace["id"],
            "title": "Update the example",
            "description": "Propose the smallest bounded change.",
        },
    ).json()
    run_response = client.post(
        f"/api/v1/tasks/{task['id']}/runs",
        json={"contextPackId": pack["id"]},
    )
    assert run_response.status_code == 201
    run = run_response.json()
    execute = client.post(
        f"/api/v1/runs/{run['id']}/execute",
        json={"providerId": "mensura.builtin"},
    )
    assert execute.status_code == 200
    return workspace, execute.json(), original


def test_create_get_and_list_change_proposal_from_successful_run(
    tmp_path: Path,
) -> None:
    from mensura_core.main import create_app

    provider = ProposalProvider(proposal_draft())
    with TestClient(create_app(provider=provider)) as client:
        workspace, run, original = create_successful_run(client, tmp_path)
        endpoint = f"/api/v1/runs/{run['id']}/change-proposals"

        response = client.post(endpoint)
        repeated = client.post(endpoint)

        assert response.status_code == 201
        assert response.headers["location"].startswith("/api/v1/change-proposals/")
        body = response.json()
        proposal = body["proposal"]
        assert body["created"] is True
        assert repeated.json() == {"proposal": proposal, "created": False}
        assert proposal["schemaVersion"] == "1"
        assert proposal["runId"] == run["id"]
        assert proposal["taskId"] == run["taskId"]
        assert proposal["workspaceId"] == workspace["id"]
        assert proposal["contextPackId"] == run["contextPackId"]
        assert proposal["providerId"] == "mensura.builtin"
        assert proposal["promptVersion"] == "review.v2"
        assert proposal["status"] == "proposed"
        assert proposal["reviewedAt"] is None
        change = proposal["fileChanges"][0]
        assert change["path"] == "src/example.py"
        assert change["changeType"] == "modify"
        assert change["beforeDigest"] == f"sha256:{sha256(original.encode()).hexdigest()}"
        proposed = "print('proposed output')\n"
        assert change["afterDigest"] == f"sha256:{sha256(proposed.encode()).hexdigest()}"
        assert change["truncated"] is False
        assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == original

        proposal_id = proposal["id"]
        assert client.get(f"/api/v1/change-proposals/{proposal_id}").json() == proposal
        collection = client.get(f"/api/v1/workspaces/{workspace['id']}/change-proposals").json()
        assert collection == {"items": [proposal], "total": 1}


def test_change_proposal_requires_a_successful_run(tmp_path: Path) -> None:
    from mensura_core.main import create_app

    with TestClient(create_app()) as client:
        workspace = client.post(
            "/api/v1/workspaces",
            json={"name": "Queued", "rootPath": str(tmp_path)},
        ).json()
        (tmp_path / "context.txt").write_text("context", encoding="utf-8")
        client.post(f"/api/v1/workspaces/{workspace['id']}/vault/inventory")
        pack = client.post(
            f"/api/v1/workspaces/{workspace['id']}/context-packs",
            json={"paths": ["context.txt"]},
        ).json()["contextPack"]
        task = client.post(
            "/api/v1/tasks",
            json={"workspaceId": workspace["id"], "title": "Queued task"},
        ).json()
        run = client.post(
            f"/api/v1/tasks/{task['id']}/runs",
            json={"contextPackId": pack["id"]},
        ).json()

        response = client.post(f"/api/v1/runs/{run['id']}/change-proposals")
        missing = client.post(f"/api/v1/runs/{uuid4()}/change-proposals")

    assert response.status_code == 409
    assert response.json()["type"] == ("urn:mensura:problem:change-proposal-run-not-eligible")
    assert missing.status_code == 404
    assert missing.json()["type"] == "urn:mensura:problem:resource-not-found"


def test_approve_and_reject_are_terminal_review_transitions(tmp_path: Path) -> None:
    from mensura_core.main import create_app

    with TestClient(create_app(provider=ProposalProvider(proposal_draft()))) as client:
        workspace, run, _ = create_successful_run(client, tmp_path)
        proposal = client.post(f"/api/v1/runs/{run['id']}/change-proposals").json()["proposal"]
        proposal_id = proposal["id"]

        approved = client.post(f"/api/v1/change-proposals/{proposal_id}/approve")
        repeated = client.post(f"/api/v1/change-proposals/{proposal_id}/reject")

        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        assert approved.json()["reviewedAt"] is not None
        assert repeated.status_code == 409
        assert repeated.json()["type"] == ("urn:mensura:problem:change-proposal-invalid-state")
        assert client.get(f"/api/v1/change-proposals/{proposal_id}").json() == approved.json()

        second_root = tmp_path / "second"
        second_workspace, second_run, _ = create_successful_run(client, second_root)
        second = client.post(f"/api/v1/runs/{second_run['id']}/change-proposals").json()["proposal"]
        rejected = client.post(f"/api/v1/change-proposals/{second['id']}/reject")
        assert rejected.json()["status"] == "rejected"
        assert second_workspace["id"] != workspace["id"]


def test_change_proposal_text_is_utf8_bounded_and_signaled(tmp_path: Path) -> None:
    from mensura_core.main import create_app

    full_text = "é" * 5_000
    with TestClient(
        create_app(provider=ProposalProvider(proposal_draft(text=full_text)))
    ) as client:
        _, run, _ = create_successful_run(client, tmp_path)
        response = client.post(f"/api/v1/runs/{run['id']}/change-proposals")

    assert response.status_code == 201
    change = response.json()["proposal"]["fileChanges"][0]
    assert change["originalTextBytes"] == 10_000
    assert change["proposedTextBytes"] <= 8_192
    assert len(change["proposedText"].encode("utf-8")) == change["proposedTextBytes"]
    assert change["truncated"] is True
    assert change["afterDigest"] == f"sha256:{sha256(full_text.encode()).hexdigest()}"


def test_oversized_or_malformed_proposal_output_uses_problem_details(
    tmp_path: Path,
) -> None:
    from mensura_core.main import create_app

    oversized = ChangeProposalDraft(
        summary="Too large",
        rationale="Exercise the explicit aggregate source limit.",
        file_changes=tuple(
            ChangeProposalDraftFileChange(
                path=f"new/file-{index}.txt",
                change_type=ChangeProposalChangeType.CREATE,
                language="Text",
                proposed_text="x" * 16_384,
            )
            for index in range(9)
        ),
    )
    with TestClient(create_app(provider=ProposalProvider(oversized))) as client:
        _, run, _ = create_successful_run(client, tmp_path / "oversized")
        too_large = client.post(f"/api/v1/runs/{run['id']}/change-proposals")

    malformed = proposal_draft(path="../escape.py")
    with TestClient(create_app(provider=ProposalProvider(malformed))) as client:
        _, run, _ = create_successful_run(client, tmp_path / "malformed")
        invalid = client.post(f"/api/v1/runs/{run['id']}/change-proposals")
        missing = client.get(f"/api/v1/change-proposals/{uuid4()}")

    assert too_large.status_code == 413
    assert too_large.headers["content-type"] == "application/problem+json"
    assert too_large.json()["type"] == ("urn:mensura:problem:change-proposal-content-too-large")
    assert invalid.status_code == 422
    assert invalid.json()["type"] == ("urn:mensura:problem:change-proposal-output-invalid")
    assert missing.status_code == 404
    assert missing.json()["type"] == "urn:mensura:problem:change-proposal-not-found"
