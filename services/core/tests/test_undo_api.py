import json
from collections.abc import Sequence
from pathlib import Path

from fastapi.testclient import TestClient
from git import Repo

from mensura_core.guard_runner import CommandExecution
from mensura_core.main import create_app
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

ORIGINAL_EXAMPLE = "print('immutable input')\n"
ORIGINAL_OLD = "print('obsolete module')\n"
PROPOSED_EXAMPLE = "print('applied output')\n"
PROPOSED_NOTE = "A newly applied bounded note.\n"


class ProposalProvider(DeterministicReviewProvider):
    def __init__(self, draft: ChangeProposalDraft) -> None:
        self._draft = draft

    def execute(self, request: ProviderExecutionRequest) -> RunExecutionResult:
        result = super().execute(request)
        return result.model_copy(update={"proposal_draft": self._draft})


class FakeGuardCommandRunner:
    def __init__(self, *, exit_code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self._exit_code = exit_code
        self._stdout = stdout
        self._stderr = stderr
        self.working_directories: list[Path] = []

    def run(self, command: Sequence[str], *, cwd: Path, timeout_seconds: float) -> CommandExecution:
        self.working_directories.append(Path(cwd))
        return CommandExecution(
            exit_code=self._exit_code,
            duration_ms=5,
            stdout=self._stdout,
            stderr=self._stderr,
            output_truncated=False,
            timed_out=False,
        )


def full_draft() -> ChangeProposalDraft:
    return ChangeProposalDraft(
        summary="Apply one bounded modify, create, and delete.",
        rationale="The captured context identifies these files as safe bounded targets.",
        file_changes=(
            ChangeProposalDraftFileChange(
                path="src/example.py",
                change_type=ChangeProposalChangeType.MODIFY,
                language="Python",
                proposed_text=PROPOSED_EXAMPLE,
            ),
            ChangeProposalDraftFileChange(
                path="docs/new-note.txt",
                change_type=ChangeProposalChangeType.CREATE,
                language="Text",
                proposed_text=PROPOSED_NOTE,
            ),
            ChangeProposalDraftFileChange(
                path="src/old.py",
                change_type=ChangeProposalChangeType.DELETE,
                language="Python",
                proposed_text=None,
            ),
        ),
    )


def write_fixture_files(root: Path, *, guard_config: bool = True) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "example.py").write_text(ORIGINAL_EXAMPLE, encoding="utf-8")
    (root / "src" / "old.py").write_text(ORIGINAL_OLD, encoding="utf-8")
    if guard_config:
        (root / ".mensura").mkdir()
        (root / ".mensura" / "guard.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "checks": {
                        "lint": {"command": ["ruff", "check", "."]},
                        "test": {"command": ["pytest"]},
                    },
                }
            ),
            encoding="utf-8",
        )


def init_repository(root: Path) -> Repo:
    repository = Repo.init(root)
    with repository.config_writer() as config:
        config.set_value("user", "name", "Mensura Test")
        config.set_value("user", "email", "test@mensura.invalid")
    repository.git.add("-A")
    repository.git.commit("-m", "Undo fixture baseline")
    return repository


def approve_verified_proposal(client: TestClient, root: Path, *, title: str = "Undo") -> dict:
    workspace = client.post(
        "/api/v1/workspaces", json={"name": title, "rootPath": str(root)}
    ).json()
    assert client.post(f"/api/v1/workspaces/{workspace['id']}/vault/inventory").status_code == 201
    pack = client.post(
        f"/api/v1/workspaces/{workspace['id']}/context-packs",
        json={"paths": ["src/example.py", "src/old.py"]},
    ).json()["contextPack"]
    task = client.post(
        "/api/v1/tasks", json={"workspaceId": workspace["id"], "title": title}
    ).json()
    run = client.post(f"/api/v1/tasks/{task['id']}/runs", json={"contextPackId": pack["id"]}).json()
    assert (
        client.post(
            f"/api/v1/runs/{run['id']}/execute", json={"providerId": "mensura.builtin"}
        ).status_code
        == 200
    )
    proposal = client.post(f"/api/v1/runs/{run['id']}/change-proposals").json()["proposal"]
    approved = client.post(f"/api/v1/change-proposals/{proposal['id']}/approve").json()
    verification = client.post(f"/api/v1/change-proposals/{proposal['id']}/verify")
    return {"proposal": approved, "verification": verification.json()}


def apply_and_return_application(client: TestClient, root: Path) -> dict:
    ready = approve_verified_proposal(client, root)
    proposal, verification = ready["proposal"], ready["verification"]
    response = client.post(
        f"/api/v1/change-proposals/{proposal['id']}/apply",
        json={"verificationId": verification["id"]},
    )
    assert response.status_code == 201
    return response.json()


def test_undo_restores_modified_file_and_removes_created_file(
    tmp_path: Path,
) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    runner = FakeGuardCommandRunner()
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        application = apply_and_return_application(client, tmp_path)
        assert application["status"] == "applied_guard_passed"
        assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == PROPOSED_EXAMPLE
        assert (tmp_path / "docs" / "new-note.txt").exists()
        assert not (tmp_path / "src" / "old.py").exists()

        response = client.post(f"/api/v1/applications/{application['id']}/undo")

    assert response.status_code == 201
    undo = response.json()
    assert response.headers["location"] == f"/api/v1/undos/{undo['id']}"
    assert undo["schemaVersion"] == "1"
    assert undo["applicationId"] == application["id"]
    assert undo["proposalId"] == application["proposalId"]
    assert undo["workspaceId"] == application["workspaceId"]
    assert undo["status"] == "undone_guard_passed"

    outcomes = {o["path"]: o for o in undo["fileOutcomes"]}
    assert outcomes["src/example.py"]["undone"] is True
    assert outcomes["src/example.py"]["action"] == "restored"
    assert outcomes["docs/new-note.txt"]["undone"] is True
    assert outcomes["docs/new-note.txt"]["action"] == "deleted"
    assert outcomes["src/old.py"]["undone"] is True
    assert outcomes["src/old.py"]["action"] == "restored"

    assert undo["guard"]["status"] == "passed"
    assert undo["guardUnavailableReason"] is None

    assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == ORIGINAL_EXAMPLE
    assert not (tmp_path / "docs" / "new-note.txt").exists()
    assert (tmp_path / "src" / "old.py").read_text(encoding="utf-8") == ORIGINAL_OLD

    fetched = client.get(f"/api/v1/undos/{undo['id']}")
    assert fetched.json() == undo
    listing = client.get(f"/api/v1/workspaces/{application['workspaceId']}/undos")
    assert listing.json() == {"items": [undo], "total": 1}


def test_undo_refuses_when_live_file_drifted(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    runner = FakeGuardCommandRunner()
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        application = apply_and_return_application(client, tmp_path)

        (tmp_path / "src" / "example.py").write_text("print('edited after apply')\n", encoding="utf-8")

        response = client.post(f"/api/v1/applications/{application['id']}/undo")

    assert response.status_code == 201
    undo = response.json()
    assert undo["status"] == "undo_refused"
    assert len(undo["fileOutcomes"]) == 0
    assert undo["guard"] is None
    assert "drifted" in (undo.get("guardUnavailableReason") or "")
    # The live file was not touched.
    assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == "print('edited after apply')\n"


def test_undo_is_single_use_per_application(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    runner = FakeGuardCommandRunner()
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        application = apply_and_return_application(client, tmp_path)

        first = client.post(f"/api/v1/applications/{application['id']}/undo")
        second = client.post(f"/api/v1/applications/{application['id']}/undo")
        listing = client.get(f"/api/v1/workspaces/{application['workspaceId']}/undos")

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["type"] == "urn:mensura:problem:undo-already-exists"
    assert listing.json()["total"] == 1


def test_undo_refuses_ineligible_application(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    runner = FakeGuardCommandRunner()
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        ready = approve_verified_proposal(client, tmp_path)
        proposal = ready["proposal"]

        response = client.post(f"/api/v1/applications/{proposal['id']}/undo")

    assert response.status_code == 404
    assert response.json()["type"] == "urn:mensura:problem:application-not-found"


def test_missing_undo_returns_problem_details(tmp_path: Path) -> None:
    from uuid import uuid4

    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/undos/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["type"] == "urn:mensura:problem:undo-not-found"


def test_undo_records_guard_failure_after_restoration(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    runner = FakeGuardCommandRunner()
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        application = apply_and_return_application(client, tmp_path)
        runner._exit_code = 1
        runner._stdout = "lint check failed"

        response = client.post(f"/api/v1/applications/{application['id']}/undo")

    assert response.status_code == 201
    undo = response.json()
    assert undo["status"] == "undone_guard_failed"
    assert undo["guard"]["status"] == "failed"
    assert undo["guard"]["blocking"] is True
    assert all(o["undone"] for o in undo["fileOutcomes"])
    assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == ORIGINAL_EXAMPLE
