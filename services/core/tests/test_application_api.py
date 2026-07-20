import json
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

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


def empty_draft() -> ChangeProposalDraft:
    return ChangeProposalDraft(
        summary="No safe change is proposed from the available evidence.",
        rationale="The captured context does not justify any bounded file change.",
        file_changes=(),
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
    repository.git.commit("-m", "Application fixture baseline")
    return repository


def approve_verified_proposal(client: TestClient, root: Path, *, title: str = "Apply") -> dict:
    """Drive the full flow to an approved proposal with a passing verification."""
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


def repository_worktree_count(repository: Repo) -> int:
    listing = repository.git.worktree("list", "--porcelain")
    return sum(line.startswith("worktree ") for line in listing.splitlines())


def digest_of(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def test_apply_writes_verified_content_to_live_tree_without_git_side_effects(
    tmp_path: Path,
) -> None:
    write_fixture_files(tmp_path)
    repository = init_repository(tmp_path)
    head_before = repository.head.commit.hexsha
    commit_count_before = sum(1 for _ in repository.iter_commits())
    runner = FakeGuardCommandRunner()
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        ready = approve_verified_proposal(client, tmp_path)
        proposal = ready["proposal"]
        verification = ready["verification"]
        assert verification["status"] == "passed"

        response = client.post(
            f"/api/v1/change-proposals/{proposal['id']}/apply",
            json={"verificationId": verification["id"]},
        )

        assert response.status_code == 201
        application = response.json()
        assert response.headers["location"] == f"/api/v1/applications/{application['id']}"
        assert application["schemaVersion"] == "1"
        assert application["proposalId"] == proposal["id"]
        assert application["verificationId"] == verification["id"]
        assert application["runId"] == proposal["runId"]
        assert application["workspaceId"] == proposal["workspaceId"]
        assert application["contextPackId"] == proposal["contextPackId"]
        assert application["status"] == "applied_guard_passed"
        assert application["target"] == {
            "kind": "live_working_tree",
            "liveCommitId": head_before,
            "verificationCommitId": head_before,
            "headMovedSinceVerification": False,
        }
        assert application["guard"]["status"] == "passed"
        assert application["guard"]["blocking"] is False
        assert application["guardUnavailableReason"] is None
        assert application["summary"] == {
            "filesTotal": 3,
            "createdCount": 1,
            "modifiedCount": 1,
            "deletedCount": 1,
            "appliedCount": 3,
            "failedCount": 0,
        }

        results = {result["path"]: result for result in application["fileResults"]}
        assert all(result["applied"] for result in results.values())
        assert all(result["reason"] == "applied" for result in results.values())
        modify = results["src/example.py"]
        assert modify["beforeDigest"] == digest_of(ORIGINAL_EXAMPLE)
        assert modify["liveBeforeDigest"] == digest_of(ORIGINAL_EXAMPLE)
        assert modify["afterDigest"] == digest_of(PROPOSED_EXAMPLE)
        assert modify["appliedDigest"] == digest_of(PROPOSED_EXAMPLE)
        create = results["docs/new-note.txt"]
        assert create["liveBeforeDigest"] is None
        assert create["appliedDigest"] == digest_of(PROPOSED_NOTE)
        delete = results["src/old.py"]
        assert delete["afterDigest"] is None
        assert delete["appliedDigest"] is None

        undo = {entry["path"]: entry for entry in application["undo"]["files"]}
        assert application["undo"]["strategy"] == "restore_prior_content"
        assert undo["src/example.py"]["priorDigest"] == digest_of(ORIGINAL_EXAMPLE)
        assert undo["src/example.py"]["priorContent"] == ORIGINAL_EXAMPLE
        assert undo["src/example.py"]["priorTruncated"] is False
        assert undo["docs/new-note.txt"]["priorExisted"] is False
        assert undo["docs/new-note.txt"]["priorContent"] is None
        assert undo["src/old.py"]["priorContent"] == ORIGINAL_OLD

        fetched = client.get(f"/api/v1/applications/{application['id']}")
        assert fetched.json() == application
        listing = client.get(f"/api/v1/workspaces/{proposal['workspaceId']}/applications")
        assert listing.json() == {"items": [application], "total": 1}

    # The verified content is now on the live working tree.
    assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == PROPOSED_EXAMPLE
    assert (tmp_path / "docs" / "new-note.txt").read_text(encoding="utf-8") == PROPOSED_NOTE
    assert not (tmp_path / "src" / "old.py").exists()

    # No commit, stage, push, or worktree side effects occurred.
    assert repository.head.commit.hexsha == head_before
    assert sum(1 for _ in repository.iter_commits()) == commit_count_before
    assert len(repository.index.diff("HEAD")) == 0
    assert repository.is_dirty(untracked_files=True)
    assert repository_worktree_count(repository) == 1
    # Guard executed once against the live root, not a temporary sandbox.
    assert runner.working_directories[-1] == tmp_path


def test_apply_is_refused_when_live_content_drifted(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    with TestClient(
        create_app(
            provider=ProposalProvider(full_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    ) as client:
        ready = approve_verified_proposal(client, tmp_path)
        proposal, verification = ready["proposal"], ready["verification"]

        # The live working tree drifts after verification but before application.
        drifted = "print('edited by a human after verification')\n"
        (tmp_path / "src" / "example.py").write_text(drifted, encoding="utf-8")

        response = client.post(
            f"/api/v1/change-proposals/{proposal['id']}/apply",
            json={"verificationId": verification["id"]},
        )
        listing = client.get(f"/api/v1/workspaces/{proposal['workspaceId']}/applications")

    assert response.status_code == 409
    assert response.json()["type"] == "urn:mensura:problem:application-live-drift"
    # Nothing was written and no artifact was persisted.
    assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == drifted
    assert (tmp_path / "src" / "old.py").read_text(encoding="utf-8") == ORIGINAL_OLD
    assert not (tmp_path / "docs").exists()
    assert listing.json() == {"items": [], "total": 0}


def test_apply_requires_an_approved_proposal(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    with TestClient(
        create_app(
            provider=ProposalProvider(full_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    ) as client:
        workspace = client.post(
            "/api/v1/workspaces", json={"name": "Unapproved", "rootPath": str(tmp_path)}
        ).json()
        client.post(f"/api/v1/workspaces/{workspace['id']}/vault/inventory")
        pack = client.post(
            f"/api/v1/workspaces/{workspace['id']}/context-packs",
            json={"paths": ["src/example.py", "src/old.py"]},
        ).json()["contextPack"]
        task = client.post(
            "/api/v1/tasks", json={"workspaceId": workspace["id"], "title": "Unapproved"}
        ).json()
        run = client.post(
            f"/api/v1/tasks/{task['id']}/runs", json={"contextPackId": pack["id"]}
        ).json()
        client.post(f"/api/v1/runs/{run['id']}/execute", json={"providerId": "mensura.builtin"})
        proposal = client.post(f"/api/v1/runs/{run['id']}/change-proposals").json()["proposal"]

        response = client.post(
            f"/api/v1/change-proposals/{proposal['id']}/apply",
            json={"verificationId": str(uuid4())},
        )

    assert response.status_code == 409
    assert response.json()["type"] == "urn:mensura:problem:application-proposal-not-approved"
    assert not (tmp_path / "docs").exists()


def test_apply_requires_a_verification_that_belongs_and_passes(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    with TestClient(
        create_app(
            provider=ProposalProvider(full_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    ) as client:
        ready = approve_verified_proposal(client, tmp_path)
        proposal = ready["proposal"]

        missing = client.post(
            f"/api/v1/change-proposals/{proposal['id']}/apply",
            json={"verificationId": str(uuid4())},
        )

    assert missing.status_code == 404
    assert missing.json()["type"] == "urn:mensura:problem:application-verification-not-found"


def test_apply_rejects_a_failed_verification(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    runner = FakeGuardCommandRunner(exit_code=1, stdout="lint failed")
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        ready = approve_verified_proposal(client, tmp_path)
        proposal, verification = ready["proposal"], ready["verification"]
        assert verification["status"] == "failed"

        response = client.post(
            f"/api/v1/change-proposals/{proposal['id']}/apply",
            json={"verificationId": verification["id"]},
        )
        listing = client.get(f"/api/v1/workspaces/{proposal['workspaceId']}/applications")

    assert response.status_code == 409
    assert response.json()["type"] == "urn:mensura:problem:application-verification-not-passed"
    assert not (tmp_path / "docs").exists()
    assert listing.json() == {"items": [], "total": 0}


def test_apply_records_live_guard_failure_after_writing(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    # Verification passes, but the live Guard run after apply fails.
    runner = FakeGuardCommandRunner()
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        ready = approve_verified_proposal(client, tmp_path)
        proposal, verification = ready["proposal"], ready["verification"]
        assert verification["status"] == "passed"

        runner._exit_code = 1  # the live Guard run now fails
        runner._stdout = "3 files would be reformatted"
        response = client.post(
            f"/api/v1/change-proposals/{proposal['id']}/apply",
            json={"verificationId": verification["id"]},
        )

    assert response.status_code == 201
    application = response.json()
    assert application["status"] == "applied_guard_failed"
    assert application["guard"]["status"] == "failed"
    assert application["guard"]["blocking"] is True
    assert all(result["applied"] for result in application["fileResults"])
    # The change is still on the live tree; Guard failure is surfaced, not reverted.
    assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == PROPOSED_EXAMPLE
    assert not (tmp_path / "src" / "old.py").exists()


def test_apply_is_single_use_per_proposal(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    with TestClient(
        create_app(
            provider=ProposalProvider(full_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    ) as client:
        ready = approve_verified_proposal(client, tmp_path)
        proposal, verification = ready["proposal"], ready["verification"]
        first = client.post(
            f"/api/v1/change-proposals/{proposal['id']}/apply",
            json={"verificationId": verification["id"]},
        )
        second = client.post(
            f"/api/v1/change-proposals/{proposal['id']}/apply",
            json={"verificationId": verification["id"]},
        )
        listing = client.get(f"/api/v1/workspaces/{proposal['workspaceId']}/applications")

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["type"] == "urn:mensura:problem:application-already-exists"
    assert listing.json()["total"] == 1


def test_apply_refuses_an_empty_proposal(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    with TestClient(
        create_app(
            provider=ProposalProvider(empty_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    ) as client:
        ready = approve_verified_proposal(client, tmp_path)
        proposal, verification = ready["proposal"], ready["verification"]
        response = client.post(
            f"/api/v1/change-proposals/{proposal['id']}/apply",
            json={"verificationId": verification["id"]},
        )

    assert response.status_code == 422
    assert response.json()["type"] == "urn:mensura:problem:application-empty-proposal"


def test_apply_refuses_when_guard_configuration_is_missing(tmp_path: Path) -> None:
    write_fixture_files(tmp_path, guard_config=False)
    init_repository(tmp_path)
    with TestClient(
        create_app(
            provider=ProposalProvider(full_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    ) as client:
        # Without Guard config the proposal cannot be verified, so seed a passing
        # verification by temporarily providing one, then remove the config.
        (tmp_path / ".mensura").mkdir()
        (tmp_path / ".mensura" / "guard.json").write_text(
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
        Repo(tmp_path).git.add("-A")
        Repo(tmp_path).git.commit("-m", "Add guard config")
        ready = approve_verified_proposal(client, tmp_path)
        proposal, verification = ready["proposal"], ready["verification"]
        assert verification["status"] == "passed"

        # The config is removed from the live tree before application.
        (tmp_path / ".mensura" / "guard.json").unlink()
        response = client.post(
            f"/api/v1/change-proposals/{proposal['id']}/apply",
            json={"verificationId": verification["id"]},
        )
        listing = client.get(f"/api/v1/workspaces/{proposal['workspaceId']}/applications")

    assert response.status_code == 404
    assert response.json()["type"] == "urn:mensura:problem:guard-configuration-not-found"
    # Guard config is checked before any write, so nothing was applied.
    assert not (tmp_path / "docs").exists()
    assert (tmp_path / "src" / "old.py").exists()
    assert listing.json() == {"items": [], "total": 0}


def test_missing_application_returns_problem_details(tmp_path: Path) -> None:
    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/applications/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["type"] == "urn:mensura:problem:application-not-found"
