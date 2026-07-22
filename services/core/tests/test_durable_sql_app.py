"""HTTP-level integration tests for the durable SQL app path.

These exercise the *real* durable configuration documented for users — the shape of
``create_sql_app`` (``run_migrations_on_startup=True``, ``use_sql=True``,
``enable_worker=True``) — against a temporary SQLite database and backup directory. The
only injected fakes are the provider and the Guard command runner (a real LLM/toolchain
is not hermetic); persistence, Alembic migrations, the job worker + its lifespan, the
workspace write reservation, and routing are all real.
"""

import sqlite3
import time
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_undo_api import (
    FakeGuardCommandRunner,
    ProposalProvider,
    apply_and_return_application,
    approve_verified_proposal,
    full_draft,
    init_repository,
    write_fixture_files,
)
from vault_fakes import FakeSemanticEmbedder

from mensura_core.main import create_app
from mensura_core.persistence.database import get_alembic_head

RANDOM_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def durable_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict]:
    """A temp SQLite DB + backup dir wired the way the durable app expects."""
    db_path = tmp_path / "core.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setenv("MENSURA_BACKUP_DIR", str(backup_dir))
    yield {"db_path": db_path, "database_url": f"sqlite:///{db_path}", "backup_dir": backup_dir}
    for suffix in ("", "-wal", "-shm"):
        Path(str(db_path) + suffix).unlink(missing_ok=True)


def _durable_app(
    database_url: str,
    *,
    with_git_provider: bool,
    enable_worker: bool,
    enable_startup_maintenance: bool = False,
) -> FastAPI:
    kwargs: dict = {
        "run_migrations_on_startup": True,
        "database_url": database_url,
        "use_sql": True,
        "enable_worker": enable_worker,
        "enable_startup_maintenance": enable_startup_maintenance,
    }
    if with_git_provider:
        kwargs["provider"] = ProposalProvider(full_draft())
        kwargs["guard_command_runner"] = FakeGuardCommandRunner()
    return create_app(**kwargs)


def _client(
    durable_env: dict, *, with_git_provider: bool = False, enable_worker: bool = True
) -> TestClient:
    app = _durable_app(
        durable_env["database_url"],
        with_git_provider=with_git_provider,
        enable_worker=enable_worker,
    )
    return TestClient(app)


def _wait_for_job(client: TestClient, job_id: str, status: str, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        if job["status"] == status:
            return job
        if job["status"] == "failed" and status != "failed":
            raise AssertionError(f"Job unexpectedly failed: {job.get('lastError')}")
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} did not reach '{status}' within {timeout}s")


# --------------------------------------------------------- startup / migrations / lifespan


def test_durable_app_starts_and_reports_health(durable_env: dict) -> None:
    with _client(durable_env) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"


def test_migrations_produce_the_expected_schema_at_head(durable_env: dict) -> None:
    with _client(durable_env):
        pass  # Booting through the factory applies migrations.

    connection = sqlite3.connect(durable_env["db_path"])
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    finally:
        connection.close()

    assert version == get_alembic_head()
    # The durable artifact chain + orchestration tables are all present.
    assert {"workspaces", "applications", "undos", "backups", "jobs"} <= tables


def test_worker_lifespan_drains_a_backup_job_to_succeeded(durable_env: dict) -> None:
    """The real background worker (started by the lifespan) executes an enqueued job."""
    with _client(durable_env) as client:
        enqueue = client.post(
            "/api/v1/jobs", json={"jobType": "backup_create", "label": "lifespan"}
        )
        assert enqueue.status_code == 201
        job_id = enqueue.json()["id"]

        finished = _wait_for_job(client, job_id, "succeeded")

        assert finished["resultEntityType"] == "backup"
        assert finished["finishedAt"] is not None
        backups = client.get("/api/v1/backups").json()
        assert backups["total"] == 1
        assert backups["items"][0]["id"] == finished["resultEntityId"]
        assert backups["items"][0]["status"] == "completed"


# ------------------------------------------------------------------ structured problems


def test_unknown_job_returns_structured_problem(durable_env: dict) -> None:
    with _client(durable_env) as client:
        resp = client.get(f"/api/v1/jobs/{RANDOM_UUID}")
        assert resp.status_code == 404
        assert resp.headers["content-type"] == "application/problem+json"
        body = resp.json()
        assert body["type"] == "urn:mensura:problem:job-not-found"
        assert body["status"] == 404


def test_backup_endpoint_smoke_path(durable_env: dict) -> None:
    with _client(durable_env) as client:
        created = client.post("/api/v1/backups", json={"label": "smoke"})
        assert created.status_code == 201
        backup = created.json()
        assert backup["status"] == "completed"
        assert backup["label"] == "smoke"

        listed = client.get("/api/v1/backups").json()
        assert listed["total"] == 1
        fetched = client.get(f"/api/v1/backups/{backup['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == backup["id"]


# ------------------------------------------------------- reservation / contention (real DB)


def test_apply_is_refused_while_the_workspace_write_reservation_is_held(
    durable_env: dict, tmp_path: Path
) -> None:
    """A held live-tree reservation refuses an incoming apply with a structured 409."""
    root = tmp_path / "workspace"
    root.mkdir()
    write_fixture_files(root)
    init_repository(root)

    app = _durable_app(durable_env["database_url"], with_git_provider=True, enable_worker=False)
    with TestClient(app) as client:
        ready = approve_verified_proposal(client, root)
        proposal, verification = ready["proposal"], ready["verification"]
        workspace_id = UUID(proposal["workspaceId"])
        example = root / "src" / "example.py"
        before = example.read_text(encoding="utf-8")

        # Simulate a concurrent live-tree writer already holding the workspace.
        reservation = client.app.state.workspace_write_reservation
        with reservation.reserve(workspace_id, holder_kind="application_undo"):
            resp = client.post(
                f"/api/v1/change-proposals/{proposal['id']}/apply",
                json={"verificationId": verification["id"]},
            )

        assert resp.status_code == 409
        assert resp.headers["content-type"] == "application/problem+json"
        assert resp.json()["type"] == "urn:mensura:problem:workspace-write-in-progress"
        # The refusal wrote nothing and persisted no application artifact.
        assert example.read_text(encoding="utf-8") == before
        apps = client.get(f"/api/v1/workspaces/{workspace_id}/applications").json()
        assert apps["total"] == 0


def test_undo_is_refused_while_an_apply_holds_the_reservation(
    durable_env: dict, tmp_path: Path
) -> None:
    """Undo respects a reservation held on behalf of apply — the two cannot interleave."""
    root = tmp_path / "workspace"
    root.mkdir()
    write_fixture_files(root)
    init_repository(root)

    app = _durable_app(durable_env["database_url"], with_git_provider=True, enable_worker=False)
    with TestClient(app) as client:
        application = apply_and_return_application(client, root)
        workspace_id = UUID(application["workspaceId"])
        restored = root / "src" / "old.py"
        assert not restored.exists()  # apply deleted it

        reservation = client.app.state.workspace_write_reservation
        with reservation.reserve(workspace_id, holder_kind="application_apply"):
            resp = client.post(f"/api/v1/applications/{application['id']}/undo")

        assert resp.status_code == 409
        assert resp.json()["type"] == "urn:mensura:problem:workspace-write-in-progress"
        # Undo was refused before any write, so no restore happened and no undo artifact exists.
        assert not restored.exists()
        undos = client.get(f"/api/v1/workspaces/{workspace_id}/undos").json()
        assert undos["total"] == 0


def test_apply_and_undo_share_one_reservation_instance(durable_env: dict) -> None:
    app = _durable_app(durable_env["database_url"], with_git_provider=False, enable_worker=False)
    with TestClient(app):
        assert (
            app.state.change_application_service._write_reservation
            is app.state.undo_service._write_reservation
        )
        assert app.state.change_application_service._write_reservation is (
            app.state.workspace_write_reservation
        )


# ------------------------------------------------ startup maintenance (sweep + retention)


def test_startup_sweeps_orphaned_verification_sandbox(
    durable_env: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The durable app removes an orphaned sandbox during its startup lifespan."""
    sandbox_root = tmp_path / "sandboxes"
    sandbox_root.mkdir()
    monkeypatch.setenv("MENSURA_SANDBOX_DIR", str(sandbox_root))
    orphan = sandbox_root / "mensura-verification-orphan"
    (orphan / "worktree").mkdir(parents=True)
    unrelated = sandbox_root / "keep-me"
    unrelated.mkdir()

    app = _durable_app(
        durable_env["database_url"],
        with_git_provider=False,
        enable_worker=False,
        enable_startup_maintenance=True,
    )
    with TestClient(app):
        pass  # entering the context runs the startup lifespan, including the sweep.

    assert not orphan.exists()  # orphaned Mensura sandbox removed at startup
    assert unrelated.exists()  # a non-Mensura directory is left untouched


def test_backup_retention_prunes_on_create(
    durable_env: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Creating a backup beyond the retention count prunes the oldest backup + its file."""
    monkeypatch.setenv("MENSURA_BACKUP_RETENTION_COUNT", "2")
    monkeypatch.setenv("MENSURA_BACKUP_RETENTION_DAYS", "0")  # count-only

    with _client(durable_env) as client:
        ids = []
        for index in range(3):
            resp = client.post("/api/v1/backups", json={"label": f"b{index}"})
            assert resp.status_code == 201
            ids.append(resp.json()["id"])

        listing = client.get("/api/v1/backups").json()
        assert listing["total"] == 2  # the oldest was pruned after the third create
        remaining = {item["id"] for item in listing["items"]}
        assert ids[0] not in remaining
        assert {ids[1], ids[2]} <= remaining
        # Filesystem deletion matched the metadata deletion.
        assert len(list(durable_env["backup_dir"].glob("*.db"))) == 2


# ------------------------------------------------------------------- Vault index (real DB)


def _write_vault_fixture(root: Path) -> None:
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "src" / "auth.py").write_text(
        "def authenticate(username, password):\n    return verify(username, password)\n",
        encoding="utf-8",
    )
    (root / "docs" / "guide.md").write_text(
        "# Guide\n\nHow authentication and login work.\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")


def test_vault_index_persists_and_survives_restart(durable_env: dict, tmp_path: Path) -> None:
    """Index through the real SQL app, then search from a fresh process on the same DB."""
    root = tmp_path / "workspace"
    root.mkdir()
    _write_vault_fixture(root)

    with _client(durable_env, enable_worker=False) as client:
        workspace_id = client.post(
            "/api/v1/workspaces", json={"name": "vault", "rootPath": str(root)}
        ).json()["id"]
        indexed = client.post("/api/v1/vault/index", json={"workspaceId": workspace_id})
        assert indexed.status_code == 201
        assert indexed.json()["summary"]["memoryItemCount"] == 3

    # A second app instance on the same database file — nothing re-indexed in-process.
    with _client(durable_env, enable_worker=False) as restarted:
        snapshot = restarted.get(f"/api/v1/vault/indexes/{workspace_id}")
        assert snapshot.status_code == 200
        assert snapshot.json()["summary"]["chunkCount"] >= 2

        search = restarted.post(
            "/api/v1/vault/search",
            json={"workspaceId": workspace_id, "query": "authenticate password"},
        )
        assert search.status_code == 200
        hits = search.json()["hits"]
        assert hits and hits[0]["path"] == "src/auth.py"

        memory = restarted.get(f"/api/v1/vault/memory/{hits[0]['memoryItemId']}")
        assert memory.status_code == 200
        assert memory.json()["item"]["path"] == "src/auth.py"

        summary = restarted.post(
            "/api/v1/vault/summarize", json={"workspaceId": workspace_id}
        )
        assert summary.status_code == 200
        assert "Python" in summary.json()["technologies"]


def test_semantic_dense_vectors_survive_restart(durable_env: dict, tmp_path: Path) -> None:
    """Index with a (fake) neural embedder through the real SQLite path, then prove the dense
    vectors round-trip and semantic search still works from a fresh process on the same DB."""
    root = tmp_path / "workspace"
    root.mkdir()
    _write_vault_fixture(root)

    def app() -> FastAPI:
        return create_app(
            run_migrations_on_startup=True,
            database_url=durable_env["database_url"],
            use_sql=True,
            vault_embedder=FakeSemanticEmbedder(),
        )

    with TestClient(app()) as client:
        workspace_id = client.post(
            "/api/v1/workspaces", json={"name": "vault", "rootPath": str(root)}
        ).json()["id"]
        indexed = client.post("/api/v1/vault/index", json={"workspaceId": workspace_id})
        assert indexed.status_code == 201
        assert indexed.json()["summary"]["embedding"]["backend"] == "ollama"
        assert indexed.json()["summary"]["embedding"]["semantic"] is True

    # A second process on the same database file — dense JSON vectors are read back, not rebuilt.
    with TestClient(app()) as restarted:
        search = restarted.post(
            "/api/v1/vault/search",
            json={"workspaceId": workspace_id, "query": "sign in"},
        )
        assert search.status_code == 200
        body = search.json()
        assert body["strategy"] == "semantic-cosine:ollama/fake-semantic"
        assert body["hits"], "semantic search over persisted dense vectors returned nothing"
        assert body["hits"][0]["path"] in {"src/auth.py", "docs/guide.md"}
