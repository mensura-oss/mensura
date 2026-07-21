"""API and real end-to-end integration for durable jobs.

Enqueue happens over HTTP; execution is driven deterministically by calling
``app.state.job_worker.process_next_job()`` (the same method the background loop calls),
so each test proves a real verify/apply/undo/backup operation runs through a job and
produces its normal artifact while the job records the lifecycle."""

import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from test_undo_api import (
    PROPOSED_EXAMPLE,
    FakeGuardCommandRunner,
    ProposalProvider,
    apply_and_return_application,
    approve_verified_proposal,
    full_draft,
    init_repository,
    write_fixture_files,
)

from mensura_core.main import create_app

RANDOM_UUID = "00000000-0000-0000-0000-000000000000"


def _git_client(tmp_path: Path) -> TestClient:
    write_fixture_files(tmp_path)
    init_repository(tmp_path)
    return TestClient(
        create_app(
            provider=ProposalProvider(full_draft()),
            guard_command_runner=FakeGuardCommandRunner(),
        )
    )


def _approve_unverified_proposal(client: TestClient, root: Path) -> tuple[dict, dict]:
    workspace = client.post(
        "/api/v1/workspaces", json={"name": "Jobs", "rootPath": str(root)}
    ).json()
    client.post(f"/api/v1/workspaces/{workspace['id']}/vault/inventory")
    pack = client.post(
        f"/api/v1/workspaces/{workspace['id']}/context-packs",
        json={"paths": ["src/example.py", "src/old.py"]},
    ).json()["contextPack"]
    task = client.post(
        "/api/v1/tasks", json={"workspaceId": workspace["id"], "title": "Jobs"}
    ).json()
    run = client.post(f"/api/v1/tasks/{task['id']}/runs", json={"contextPackId": pack["id"]}).json()
    client.post(f"/api/v1/runs/{run['id']}/execute", json={"providerId": "mensura.builtin"})
    proposal = client.post(f"/api/v1/runs/{run['id']}/change-proposals").json()["proposal"]
    approved = client.post(f"/api/v1/change-proposals/{proposal['id']}/approve").json()
    return workspace, approved


# ------------------------------------------------------------------- enqueue over HTTP


def test_enqueue_verification_job_returns_queued(tmp_path: Path) -> None:
    with _git_client(tmp_path) as client:
        workspace, proposal = _approve_unverified_proposal(client, tmp_path)

        resp = client.post(
            "/api/v1/jobs",
            json={"jobType": "proposal_verification", "proposalId": proposal["id"]},
        )

        assert resp.status_code == 201
        job = resp.json()
        assert job["status"] == "queued"
        assert job["schemaVersion"] == "1"
        assert job["jobType"] == "proposal_verification"
        assert job["targetEntityType"] == "change_proposal"
        assert job["targetEntityId"] == proposal["id"]
        assert job["workspaceId"] == workspace["id"]
        assert job["payload"]["proposalId"] == proposal["id"]
        assert job["resultEntityId"] is None
        assert job["startedAt"] is None
        assert resp.headers["location"] == f"/api/v1/jobs/{job['id']}"


def test_enqueue_unknown_proposal_returns_404(tmp_path: Path) -> None:
    with _git_client(tmp_path) as client:
        resp = client.post(
            "/api/v1/jobs",
            json={"jobType": "proposal_verification", "proposalId": RANDOM_UUID},
        )
        assert resp.status_code == 404
        assert resp.json()["type"] == "urn:mensura:problem:change-proposal-not-found"


def test_enqueue_malformed_body_returns_422(tmp_path: Path) -> None:
    with _git_client(tmp_path) as client:
        assert client.post("/api/v1/jobs", json={"jobType": "bogus"}).status_code == 422
        # Missing verificationId for an apply job.
        resp = client.post(
            "/api/v1/jobs",
            json={"jobType": "application_apply", "proposalId": RANDOM_UUID},
        )
        assert resp.status_code == 422


def test_get_unknown_job_returns_404(tmp_path: Path) -> None:
    with _git_client(tmp_path) as client:
        resp = client.get(f"/api/v1/jobs/{RANDOM_UUID}")
        assert resp.status_code == 404
        assert resp.json()["type"] == "urn:mensura:problem:job-not-found"


def test_list_jobs_filters_by_status_and_type(tmp_path: Path) -> None:
    with _git_client(tmp_path) as client:
        _workspace, proposal = _approve_unverified_proposal(client, tmp_path)
        client.post(
            "/api/v1/jobs",
            json={"jobType": "proposal_verification", "proposalId": proposal["id"]},
        )
        client.post("/api/v1/jobs", json={"jobType": "backup_create", "label": "nightly"})

        listing = client.get("/api/v1/jobs").json()
        assert listing["total"] == 2

        queued = client.get("/api/v1/jobs", params={"status": "queued"}).json()
        assert queued["total"] == 2
        assert client.get("/api/v1/jobs", params={"status": "succeeded"}).json()["total"] == 0

        backups = client.get("/api/v1/jobs", params={"jobType": "backup_create"}).json()
        assert backups["total"] == 1
        assert backups["items"][0]["payload"]["label"] == "nightly"


# ------------------------------------------------------- real worker execution per type


def test_verification_job_runs_and_produces_a_verification_artifact(tmp_path: Path) -> None:
    with _git_client(tmp_path) as client:
        _workspace, proposal = _approve_unverified_proposal(client, tmp_path)
        job = client.post(
            "/api/v1/jobs",
            json={"jobType": "proposal_verification", "proposalId": proposal["id"]},
        ).json()

        finished = client.app.state.job_worker.process_next_job()

        assert finished is not None
        assert finished.status.value == "succeeded"
        assert finished.result_entity_type == "verification"
        # The verification artifact exists and matches the job's recorded result.
        verifications = client.get(
            f"/api/v1/change-proposals/{proposal['id']}/verifications"
        ).json()
        assert verifications["total"] == 1
        assert str(finished.result_entity_id) == verifications["items"][0]["id"]
        assert verifications["items"][0]["status"] == "passed"
        # The job is durably succeeded over REST.
        got = client.get(f"/api/v1/jobs/{job['id']}").json()
        assert got["status"] == "succeeded"
        assert got["resultEntityType"] == "verification"
        assert got["finishedAt"] is not None
        # Queue is now drained.
        assert client.app.state.job_worker.process_next_job() is None


def test_apply_job_runs_and_writes_the_live_tree(tmp_path: Path) -> None:
    with _git_client(tmp_path) as client:
        ready = approve_verified_proposal(client, tmp_path)
        proposal, verification = ready["proposal"], ready["verification"]
        job = client.post(
            "/api/v1/jobs",
            json={
                "jobType": "application_apply",
                "proposalId": proposal["id"],
                "verificationId": verification["id"],
            },
        ).json()
        assert job["status"] == "queued"

        finished = client.app.state.job_worker.process_next_job()

        assert finished is not None
        assert finished.status.value == "succeeded"
        assert finished.result_entity_type == "application"
        application = client.get(f"/api/v1/applications/{finished.result_entity_id}").json()
        assert application["status"] == "applied_guard_passed"
        assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == PROPOSED_EXAMPLE


def test_undo_job_runs_and_restores_the_live_tree(tmp_path: Path) -> None:
    with _git_client(tmp_path) as client:
        application = apply_and_return_application(client, tmp_path)
        assert not (tmp_path / "src" / "old.py").exists()

        job = client.post(
            "/api/v1/jobs",
            json={"jobType": "application_undo", "applicationId": application["id"]},
        ).json()
        assert job["targetEntityType"] == "application"

        finished = client.app.state.job_worker.process_next_job()

        assert finished is not None
        assert finished.status.value == "succeeded"
        assert finished.result_entity_type == "undo"
        undo = client.get(f"/api/v1/undos/{finished.result_entity_id}").json()
        assert undo["status"] == "undone_guard_passed"
        assert (tmp_path / "src" / "old.py").exists()  # restored


def test_apply_job_fails_on_live_drift_without_writing(tmp_path: Path) -> None:
    with _git_client(tmp_path) as client:
        ready = approve_verified_proposal(client, tmp_path)
        proposal, verification = ready["proposal"], ready["verification"]
        # Drift the live tree so the digest-checked apply must refuse before any write.
        (tmp_path / "src" / "example.py").write_text("print('drifted')\n", encoding="utf-8")

        client.post(
            "/api/v1/jobs",
            json={
                "jobType": "application_apply",
                "proposalId": proposal["id"],
                "verificationId": verification["id"],
            },
        )
        finished = client.app.state.job_worker.process_next_job()

        assert finished is not None
        assert finished.status.value == "failed"
        assert finished.result_entity_id is None
        assert "drift" in finished.last_error.lower()
        # The refusal wrote nothing and persisted no application artifact.
        assert (tmp_path / "src" / "example.py").read_text(encoding="utf-8") == "print('drifted')\n"
        apps = client.get(f"/api/v1/workspaces/{proposal['workspaceId']}/applications").json()
        assert apps["total"] == 0


def test_backup_job_runs_end_to_end_with_sql(tmp_path: Path) -> None:
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="mensura_jobs_backup_")
    os.close(fd)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    old_env = os.environ.get("MENSURA_BACKUP_DIR")
    os.environ["MENSURA_BACKUP_DIR"] = str(backup_dir)
    try:
        with TestClient(
            create_app(
                run_migrations_on_startup=True,
                database_url=f"sqlite:///{db_path}",
                use_sql=True,
            )
        ) as client:
            resp = client.post("/api/v1/jobs", json={"jobType": "backup_create", "label": "job"})
            assert resp.status_code == 201
            assert resp.json()["targetEntityType"] == "database"
            assert resp.json()["targetEntityId"] is None

            finished = client.app.state.job_worker.process_next_job()
            assert finished is not None
            assert finished.status.value == "succeeded"
            assert finished.result_entity_type == "backup"

            backups = client.get("/api/v1/backups").json()
            assert backups["total"] == 1
            assert str(finished.result_entity_id) == backups["items"][0]["id"]
            assert backups["items"][0]["status"] == "completed"
    finally:
        if old_env is not None:
            os.environ["MENSURA_BACKUP_DIR"] = old_env
        else:
            os.environ.pop("MENSURA_BACKUP_DIR", None)
        Path(db_path).unlink(missing_ok=True)
