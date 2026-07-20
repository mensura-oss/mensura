import json
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from git import Repo

from mensura_core.exceptions import VerificationSandboxError
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
PROPOSED_EXAMPLE = "print('proposed output')\n"
PROPOSED_NOTE = "A new bounded note.\n"


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

    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
    ) -> CommandExecution:
        self.working_directories.append(Path(cwd))
        return CommandExecution(
            exit_code=self._exit_code,
            duration_ms=7,
            stdout=self._stdout,
            stderr=self._stderr,
            output_truncated=False,
            timed_out=False,
        )


class FailingSandboxFactory:
    def create(self, workspace_root: str) -> object:
        raise VerificationSandboxError("Git could not create a temporary verification worktree.")


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
    repository.git.commit("-m", "Verification fixture baseline")
    return repository


def create_approved_proposal(client: TestClient, root: Path) -> dict:
    workspace = client.post(
        "/api/v1/workspaces",
        json={"name": "Verify", "rootPath": str(root)},
    ).json()
    assert client.post(f"/api/v1/workspaces/{workspace['id']}/vault/inventory").status_code == 201
    pack_response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/context-packs",
        json={"paths": ["src/example.py", "src/old.py"]},
    )
    assert pack_response.status_code == 201
    pack = pack_response.json()["contextPack"]
    task = client.post(
        "/api/v1/tasks",
        json={"workspaceId": workspace["id"], "title": "Verify the proposal"},
    ).json()
    run = client.post(
        f"/api/v1/tasks/{task['id']}/runs",
        json={"contextPackId": pack["id"]},
    ).json()
    execute = client.post(
        f"/api/v1/runs/{run['id']}/execute",
        json={"providerId": "mensura.builtin"},
    )
    assert execute.status_code == 200
    proposal = client.post(f"/api/v1/runs/{run['id']}/change-proposals").json()["proposal"]
    approved = client.post(f"/api/v1/change-proposals/{proposal['id']}/approve")
    assert approved.status_code == 200
    return approved.json()


def repository_worktree_count(repository: Repo) -> int:
    listing = repository.git.worktree("list", "--porcelain")
    return sum(line.startswith("worktree ") for line in listing.splitlines())


def digest_of(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def test_approved_proposal_verifies_in_isolated_sandbox_without_live_writes(
    tmp_path: Path,
) -> None:
    write_fixture_files(tmp_path)
    repository = init_repository(tmp_path)
    runner = FakeGuardCommandRunner()
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        proposal = create_approved_proposal(client, tmp_path)

        response = client.post(f"/api/v1/change-proposals/{proposal['id']}/verify")

        assert response.status_code == 201
        verification = response.json()
        assert response.headers["location"] == f"/api/v1/verifications/{verification['id']}"
        assert verification["schemaVersion"] == "1"
        assert verification["proposalId"] == proposal["id"]
        assert verification["runId"] == proposal["runId"]
        assert verification["taskId"] == proposal["taskId"]
        assert verification["workspaceId"] == proposal["workspaceId"]
        assert verification["contextPackId"] == proposal["contextPackId"]
        assert verification["status"] == "passed"
        assert verification["outcome"] == "sandbox_verified"
        assert verification["sandbox"] == {
            "kind": "git_worktree",
            "commitId": repository.head.commit.hexsha,
            "cleanupCompleted": True,
        }
        assert verification["guard"]["status"] == "passed"
        assert verification["guard"]["blocking"] is False
        assert verification["guard"]["summary"]["totalCount"] == 2
        assert verification["guard"]["summary"]["passedCount"] == 2

        results = {result["path"]: result for result in verification["fileResults"]}
        assert set(results) == {"src/example.py", "docs/new-note.txt", "src/old.py"}
        assert all(result["appliedInSandbox"] for result in results.values())
        assert all(result["reason"] == "applied" for result in results.values())
        modify = results["src/example.py"]
        assert modify["beforeDigest"] == digest_of(ORIGINAL_EXAMPLE)
        assert modify["sandboxDigest"] == digest_of(ORIGINAL_EXAMPLE)
        assert modify["afterDigest"] == digest_of(PROPOSED_EXAMPLE)
        assert results["docs/new-note.txt"]["sandboxDigest"] is None
        assert results["src/old.py"]["afterDigest"] is None
        assert verification["safeDiff"] == {
            "filesTotal": 3,
            "createdCount": 1,
            "modifiedCount": 1,
            "deletedCount": 1,
            "appliedCount": 3,
            "unappliedCount": 0,
            "proposedBytesTotal": len(PROPOSED_EXAMPLE) + len(PROPOSED_NOTE),
        }

        fetched = client.get(f"/api/v1/verifications/{verification['id']}")
        assert fetched.json() == verification
        collection = client.get(f"/api/v1/change-proposals/{proposal['id']}/verifications")
        assert collection.json() == {"items": [verification], "total": 1}

    # The live repository branch and working tree stay untouched.
    assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == ORIGINAL_EXAMPLE
    assert (tmp_path / "src" / "old.py").read_text(encoding="utf-8") == ORIGINAL_OLD
    assert not (tmp_path / "docs").exists()
    assert not repository.is_dirty(untracked_files=True)
    assert repository_worktree_count(repository) == 1

    # Guard executed inside the temporary sandbox, which no longer exists.
    assert len(runner.working_directories) == 2
    sandbox_cwd = runner.working_directories[0]
    assert not sandbox_cwd.is_relative_to(tmp_path)
    assert not sandbox_cwd.exists()


def test_verification_requires_an_approved_proposal(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    with TestClient(
        create_app(
            provider=ProposalProvider(full_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    ) as client:
        workspace = client.post(
            "/api/v1/workspaces",
            json={"name": "Unapproved", "rootPath": str(tmp_path)},
        ).json()
        client.post(f"/api/v1/workspaces/{workspace['id']}/vault/inventory")
        pack = client.post(
            f"/api/v1/workspaces/{workspace['id']}/context-packs",
            json={"paths": ["src/example.py", "src/old.py"]},
        ).json()["contextPack"]
        task = client.post(
            "/api/v1/tasks",
            json={"workspaceId": workspace["id"], "title": "Unapproved"},
        ).json()
        run = client.post(
            f"/api/v1/tasks/{task['id']}/runs",
            json={"contextPackId": pack["id"]},
        ).json()
        client.post(f"/api/v1/runs/{run['id']}/execute", json={"providerId": "mensura.builtin"})
        proposal = client.post(f"/api/v1/runs/{run['id']}/change-proposals").json()["proposal"]

        proposed = client.post(f"/api/v1/change-proposals/{proposal['id']}/verify")
        client.post(f"/api/v1/change-proposals/{proposal['id']}/reject")
        rejected = client.post(f"/api/v1/change-proposals/{proposal['id']}/verify")
        missing = client.post(f"/api/v1/change-proposals/{uuid4()}/verify")

    assert proposed.status_code == 409
    assert proposed.json()["type"] == "urn:mensura:problem:verification-proposal-not-approved"
    assert rejected.status_code == 409
    assert missing.status_code == 404
    assert missing.json()["type"] == "urn:mensura:problem:change-proposal-not-found"


def test_verification_captures_guard_failure_as_failed_artifact(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    repository = init_repository(tmp_path)
    runner = FakeGuardCommandRunner(exit_code=1, stdout="2 files would be reformatted")
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        proposal = create_approved_proposal(client, tmp_path)
        response = client.post(f"/api/v1/change-proposals/{proposal['id']}/verify")

    assert response.status_code == 201
    verification = response.json()
    assert verification["status"] == "failed"
    assert verification["outcome"] == "guard_failed"
    assert verification["guard"]["status"] == "failed"
    assert verification["guard"]["blocking"] is True
    assert verification["guard"]["summary"]["failedCount"] == 2
    excerpts = [check["outputExcerpt"] for check in verification["guard"]["checks"]]
    assert all("2 files would be reformatted" in excerpt for excerpt in excerpts)
    assert all(result["appliedInSandbox"] for result in verification["fileResults"])
    assert verification["sandbox"]["cleanupCompleted"] is True
    assert not repository.is_dirty(untracked_files=True)
    assert repository_worktree_count(repository) == 1


def test_verification_records_materialization_mismatch_without_guard(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    repository = init_repository(tmp_path)
    runner = FakeGuardCommandRunner()
    with TestClient(
        create_app(provider=ProposalProvider(full_draft()), guard_command_runner=runner)
    ) as client:
        proposal = create_approved_proposal(client, tmp_path)
        drifted = "print('drifted after approval')\n"
        (tmp_path / "src" / "example.py").write_text(drifted, encoding="utf-8")
        repository.git.add("-A")
        repository.git.commit("-m", "Drift the modify target")

        response = client.post(f"/api/v1/change-proposals/{proposal['id']}/verify")

    assert response.status_code == 201
    verification = response.json()
    assert verification["status"] == "failed"
    assert verification["outcome"] == "materialization_failed"
    assert verification["guard"] is None
    results = {result["path"]: result for result in verification["fileResults"]}
    mismatch = results["src/example.py"]
    assert mismatch["appliedInSandbox"] is False
    assert mismatch["reason"] == "before_content_mismatch"
    assert mismatch["sandboxDigest"] == digest_of(drifted)
    assert verification["safeDiff"]["unappliedCount"] == 1
    assert verification["safeDiff"]["appliedCount"] == 2
    assert runner.working_directories == []
    assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == drifted
    assert repository_worktree_count(repository) == 1


def test_verification_rejects_workspaces_that_are_not_git_repositories(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    with TestClient(
        create_app(
            provider=ProposalProvider(full_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    ) as client:
        proposal = create_approved_proposal(client, tmp_path)
        response = client.post(f"/api/v1/change-proposals/{proposal['id']}/verify")
        collection = client.get(f"/api/v1/change-proposals/{proposal['id']}/verifications")

    assert response.status_code == 422
    assert response.json()["type"] == "urn:mensura:problem:not-a-git-repository"
    assert collection.json() == {"items": [], "total": 0}


def test_verification_surfaces_sandbox_creation_failure(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    with TestClient(
        create_app(
            provider=ProposalProvider(full_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
            verification_sandbox_factory=FailingSandboxFactory(),
        )
    ) as client:
        proposal = create_approved_proposal(client, tmp_path)
        response = client.post(f"/api/v1/change-proposals/{proposal['id']}/verify")

    assert response.status_code == 500
    assert response.json()["type"] == "urn:mensura:problem:verification-sandbox-failed"


def test_verification_rejects_truncated_proposal_content(tmp_path: Path) -> None:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    truncated_draft = ChangeProposalDraft(
        summary="Oversized text is stored truncated.",
        rationale="Truncated stored bodies cannot be materialized faithfully.",
        file_changes=(
            ChangeProposalDraftFileChange(
                path="src/example.py",
                change_type=ChangeProposalChangeType.MODIFY,
                language="Python",
                proposed_text="é" * 5_000,
            ),
        ),
    )
    with TestClient(
        create_app(
            provider=ProposalProvider(truncated_draft),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    ) as client:
        proposal = create_approved_proposal(client, tmp_path)
        response = client.post(f"/api/v1/change-proposals/{proposal['id']}/verify")

    assert response.status_code == 422
    assert response.json()["type"] == "urn:mensura:problem:verification-content-incomplete"


def test_verification_cleans_up_sandbox_when_guard_configuration_is_missing(
    tmp_path: Path,
) -> None:
    write_fixture_files(tmp_path, guard_config=False)
    repository = init_repository(tmp_path)
    with TestClient(
        create_app(
            provider=ProposalProvider(full_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    ) as client:
        proposal = create_approved_proposal(client, tmp_path)
        response = client.post(f"/api/v1/change-proposals/{proposal['id']}/verify")
        collection = client.get(f"/api/v1/change-proposals/{proposal['id']}/verifications")

    assert response.status_code == 404
    assert response.json()["type"] == "urn:mensura:problem:guard-configuration-not-found"
    assert collection.json() == {"items": [], "total": 0}
    assert repository_worktree_count(repository) == 1
    assert not repository.is_dirty(untracked_files=True)


def test_missing_verification_artifact_returns_problem_details(tmp_path: Path) -> None:
    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/verifications/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["type"] == "urn:mensura:problem:verification-not-found"


def test_safe_target_refuses_symlinked_path_components(tmp_path: Path) -> None:
    from mensura_core.verification_service import ProposalVerificationService

    sandbox = tmp_path / "sandbox"
    (sandbox / "real").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (sandbox / "linked").symlink_to(outside, target_is_directory=True)
    real_file = sandbox / "real" / "safe.txt"
    real_file.write_text("safe", encoding="utf-8")
    (sandbox / "real" / "alias.txt").symlink_to(real_file)

    resolve = ProposalVerificationService._safe_target
    assert resolve(sandbox, "linked/escape.txt") is None
    assert resolve(sandbox, "real/alias.txt") is None
    assert resolve(sandbox, "real/safe.txt") == real_file
