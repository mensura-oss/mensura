import os
import tempfile
from datetime import UTC
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from mensura_core.main import create_app


def _temp_db() -> tuple[str, str]:
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="mensura_restart_")
    os.close(fd)
    return f"sqlite:///{db_path}", db_path


def test_migrations_create_clean_schema() -> None:
    import sqlalchemy as sa

    from mensura_core.persistence.database import (
        create_persistence_engine,
        create_session_factory,
        run_migrations,
    )

    db_url, db_path = _temp_db()
    try:
        run_migrations(db_url)
        engine = create_persistence_engine(db_url)
        sf = create_session_factory(engine)
        with sf() as session:
            connection = session.connection()
            result = connection.execute(
                sa.text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            tables = {row[0] for row in result}
        expected = {
            "applications",
            "backups",
            "change_proposals",
            "context_packs",
            "guard_runs",
            "jobs",
            "proposal_verifications",
            "runs",
            "tasks",
            "undos",
            "vault_chunk_postings",
            "vault_chunks",
            "vault_index_snapshots",
            "vault_inventory_items",
            "vault_inventory_snapshots",
            "vault_memory_items",
            "workspaces",
        }
        for table in expected:
            assert table in tables, f"Missing table: {table}"
        for table in tables:
            if table != "alembic_version":
                assert table in expected, f"Unexpected table: {table}"
        engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_migrations_are_reversible() -> None:
    import sqlalchemy as sa
    from alembic import command as alembic_command
    from alembic.config import Config as AlembicConfig

    from mensura_core.persistence.database import create_persistence_engine, run_migrations

    db_url, db_path = _temp_db()
    try:
        run_migrations(db_url)
        engine = create_persistence_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'"))
            assert len(list(result)) >= 10
        engine.dispose()

        migrations_dir = (
            Path(__file__).resolve().parent.parent / "src" / "mensura_core" / "migrations"
        )
        alembic_cfg = AlembicConfig(str(migrations_dir / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(migrations_dir))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_command.downgrade(alembic_cfg, "base")

        engine2 = create_persistence_engine(db_url)
        with engine2.connect() as conn:
            result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
        assert "workspaces" not in tables
        engine2.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_workspace_survives_restart() -> None:
    db_url, db_path = _temp_db()
    try:
        workspace_id = None
        with TestClient(
            create_app(run_migrations_on_startup=True, database_url=db_url, use_sql=True)
        ) as client:
            response = client.post(
                "/api/v1/workspaces",
                json={"name": "persistent workspace", "rootPath": "/tmp/mensura-persist-test"},
            )
            assert response.status_code == 201
            workspace_id = response.json()["id"]

        assert workspace_id is not None

        with TestClient(
            create_app(run_migrations_on_startup=False, database_url=db_url, use_sql=True)
        ) as client2:
            response = client2.get("/api/v1/workspaces")
            assert response.status_code == 200
            items = response.json()["items"]
            assert len(items) == 1
            assert items[0]["id"] == workspace_id
            assert items[0]["name"] == "persistent workspace"
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_task_survives_restart() -> None:
    db_url, db_path = _temp_db()
    try:
        task_id = None
        workspace_id = None
        with TestClient(
            create_app(run_migrations_on_startup=True, database_url=db_url, use_sql=True)
        ) as client:
            ws_resp = client.post(
                "/api/v1/workspaces",
                json={"name": "task test", "rootPath": "/tmp/mensura-task-test"},
            )
            workspace_id = ws_resp.json()["id"]
            task_resp = client.post(
                "/api/v1/tasks",
                json={
                    "workspaceId": workspace_id,
                    "title": "persistent task",
                    "description": "survives restart",
                    "assignedRole": "coder",
                },
            )
            assert task_resp.status_code == 201
            task_id = task_resp.json()["id"]

        with TestClient(
            create_app(run_migrations_on_startup=False, database_url=db_url, use_sql=True)
        ) as client2:
            response = client2.get(f"/api/v1/tasks/{task_id}")
            assert response.status_code == 200
            assert response.json()["title"] == "persistent task"
            assert response.json()["workspaceId"] == workspace_id
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_run_creation_survives_restart() -> None:
    db_url, db_path = _temp_db()
    try:
        workspace_id = None
        run_id = None
        with TestClient(
            create_app(run_migrations_on_startup=True, database_url=db_url, use_sql=True)
        ) as client:
            ws_resp = client.post(
                "/api/v1/workspaces",
                json={"name": "run test", "rootPath": "/tmp/mensura-run-test"},
            )
            workspace_id = ws_resp.json()["id"]
            task_resp = client.post(
                "/api/v1/tasks",
                json={
                    "workspaceId": workspace_id,
                    "title": "run test task",
                    "description": "survives",
                    "assignedRole": "coder",
                },
            )
            task_id = task_resp.json()["id"]

            import subprocess

            subprocess.run(
                ["mkdir", "-p", "/tmp/mensura-run-test"],
                capture_output=True,
            )
            Path("/tmp/mensura-run-test/context.txt").write_text("test context\n", encoding="utf-8")

            inv_resp = client.post(f"/api/v1/workspaces/{workspace_id}/vault/inventory")
            inv_resp.raise_for_status()

            cp_resp = client.post(
                f"/api/v1/workspaces/{workspace_id}/context-packs",
                json={"paths": ["context.txt"]},
            )
            cp_resp.raise_for_status()
            pack_id = cp_resp.json()["contextPack"]["id"]

            run_resp = client.post(
                f"/api/v1/tasks/{task_id}/runs",
                json={"contextPackId": pack_id},
            )
            assert run_resp.status_code == 201
            run_id = run_resp.json()["id"]

        with TestClient(
            create_app(run_migrations_on_startup=False, database_url=db_url, use_sql=True)
        ) as client2:
            response = client2.get(f"/api/v1/runs/{run_id}")
            assert response.status_code == 200
            assert response.json()["status"] == "queued"
            assert response.json()["taskId"] == task_id
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_workspace_task_list_survives_restart_with_latest_run() -> None:
    db_url, db_path = _temp_db()
    root = "/tmp/mensura-task-list-test"
    try:
        workspace_id = None
        first_task_id = None
        second_task_id = None
        run_id = None
        with TestClient(
            create_app(run_migrations_on_startup=True, database_url=db_url, use_sql=True)
        ) as client:
            ws_resp = client.post(
                "/api/v1/workspaces",
                json={"name": "task list test", "rootPath": root},
            )
            workspace_id = ws_resp.json()["id"]
            first_task_id = client.post(
                "/api/v1/tasks",
                json={"workspaceId": workspace_id, "title": "first"},
            ).json()["id"]
            second_task_id = client.post(
                "/api/v1/tasks",
                json={"workspaceId": workspace_id, "title": "second"},
            ).json()["id"]

            Path(root).mkdir(parents=True, exist_ok=True)
            Path(f"{root}/context.txt").write_text("test context\n", encoding="utf-8")
            client.post(f"/api/v1/workspaces/{workspace_id}/vault/inventory").raise_for_status()
            pack_id = client.post(
                f"/api/v1/workspaces/{workspace_id}/context-packs",
                json={"paths": ["context.txt"]},
            ).json()["contextPack"]["id"]
            run_id = client.post(
                f"/api/v1/tasks/{first_task_id}/runs",
                json={"contextPackId": pack_id},
            ).json()["id"]

        with TestClient(
            create_app(run_migrations_on_startup=False, database_url=db_url, use_sql=True)
        ) as client2:
            listed = client2.get(f"/api/v1/workspaces/{workspace_id}/tasks")
            assert listed.status_code == 200
            body = listed.json()
            assert body["total"] == 2
            by_id = {item["id"]: item for item in body["items"]}
            assert by_id[first_task_id]["latestRun"]["id"] == run_id
            assert by_id[first_task_id]["latestRun"]["status"] == "queued"
            assert by_id[second_task_id]["latestRun"] is None
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_change_proposal_lineage_survives_restart() -> None:
    db_url, db_path = _temp_db()
    try:
        workspace_id = None
        task_id = None
        run_id = None
        proposal_id = None
        with TestClient(
            create_app(run_migrations_on_startup=True, database_url=db_url, use_sql=True)
        ) as client:
            ws_resp = client.post(
                "/api/v1/workspaces",
                json={"name": "lineage test", "rootPath": "/tmp/mensura-lineage-test"},
            )
            workspace_id = ws_resp.json()["id"]
            task_resp = client.post(
                "/api/v1/tasks",
                json={
                    "workspaceId": workspace_id,
                    "title": "lineage task",
                    "description": "survives",
                    "assignedRole": "coder",
                },
            )
            task_id = task_resp.json()["id"]

            subprocess = __import__("subprocess")
            subprocess.run(
                ["mkdir", "-p", "/tmp/mensura-lineage-test"],
                capture_output=True,
            )
            Path("/tmp/mensura-lineage-test/context.txt").write_text(
                "lineage context\n", encoding="utf-8"
            )

            client.post(f"/api/v1/workspaces/{workspace_id}/vault/inventory")
            cp_resp = client.post(
                f"/api/v1/workspaces/{workspace_id}/context-packs",
                json={"paths": ["context.txt"]},
            )
            pack_id = cp_resp.json()["contextPack"]["id"]

            run_resp = client.post(
                f"/api/v1/tasks/{task_id}/runs",
                json={"contextPackId": pack_id},
            )
            run_id = run_resp.json()["id"]

            exec_resp = client.post(
                f"/api/v1/runs/{run_id}/execute",
                json={"providerId": "mensura.builtin"},
            )
            assert exec_resp.status_code == 200

            prop_resp = client.post(f"/api/v1/runs/{run_id}/change-proposals")
            if prop_resp.status_code == 201:
                proposal_id = prop_resp.json()["proposal"]["id"]

        with TestClient(
            create_app(run_migrations_on_startup=False, database_url=db_url, use_sql=True)
        ) as client2:
            resp = client2.get(f"/api/v1/workspaces/{workspace_id}/change-proposals")
            assert resp.status_code == 200
            if proposal_id is not None:
                resp2 = client2.get(f"/api/v1/change-proposals/{proposal_id}")
                assert resp2.status_code == 200
                assert resp2.json()["workspaceId"] == workspace_id

            resp3 = client2.get(f"/api/v1/runs/{run_id}")
            assert resp3.status_code == 200
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_verification_survives_restart() -> None:
    db_url, db_path = _temp_db()
    try:
        workspace_id = None
        with TestClient(
            create_app(run_migrations_on_startup=True, database_url=db_url, use_sql=True)
        ) as client:
            ws_resp = client.post(
                "/api/v1/workspaces",
                json={"name": "verify test", "rootPath": "/tmp/mensura-verify-test"},
            )
            workspace_id = ws_resp.json()["id"]

        with TestClient(
            create_app(run_migrations_on_startup=False, database_url=db_url, use_sql=True)
        ) as client2:
            resp = client2.get(f"/api/v1/workspaces/{workspace_id}/applications")
            assert resp.status_code == 200
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_application_survives_restart() -> None:
    db_url, db_path = _temp_db()
    try:
        workspace_id = None
        with TestClient(
            create_app(run_migrations_on_startup=True, database_url=db_url, use_sql=True)
        ) as client:
            ws_resp = client.post(
                "/api/v1/workspaces",
                json={"name": "app persistence", "rootPath": "/tmp/mensura-app-test"},
            )
            workspace_id = ws_resp.json()["id"]

        with TestClient(
            create_app(run_migrations_on_startup=False, database_url=db_url, use_sql=True)
        ) as client2:
            resp = client2.get(f"/api/v1/workspaces/{workspace_id}/applications")
            assert resp.status_code == 200
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_immutable_artifact_retrieval_after_restart() -> None:
    db_url, db_path = _temp_db()
    try:
        workspace_id = None
        run_id = None
        with TestClient(
            create_app(run_migrations_on_startup=True, database_url=db_url, use_sql=True)
        ) as client:
            ws_resp = client.post(
                "/api/v1/workspaces",
                json={"name": "immutable test", "rootPath": "/tmp/mensura-immutable-test"},
            )
            workspace_id = ws_resp.json()["id"]
            task_resp = client.post(
                "/api/v1/tasks",
                json={
                    "workspaceId": workspace_id,
                    "title": "immutable task",
                    "description": "survives",
                    "assignedRole": "coder",
                },
            )
            task_id = task_resp.json()["id"]

            subprocess = __import__("subprocess")
            subprocess.run(
                ["mkdir", "-p", "/tmp/mensura-immutable-test"],
                capture_output=True,
            )
            Path("/tmp/mensura-immutable-test/ctx.txt").write_text("immutable\n", encoding="utf-8")

            client.post(f"/api/v1/workspaces/{workspace_id}/vault/inventory")
            cp_resp = client.post(
                f"/api/v1/workspaces/{workspace_id}/context-packs",
                json={"paths": ["ctx.txt"]},
            )
            pack = cp_resp.json()["contextPack"]

            run_resp = client.post(
                f"/api/v1/tasks/{task_id}/runs",
                json={"contextPackId": pack["id"]},
            )
            run_id = run_resp.json()["id"]

        with TestClient(
            create_app(run_migrations_on_startup=False, database_url=db_url, use_sql=True)
        ) as client2:
            resp = client2.get(f"/api/v1/runs/{run_id}")
            assert resp.status_code == 200
            retrieved = resp.json()
            assert retrieved["contextPackId"] == pack["id"]
            assert retrieved["contextPack"]["id"] == pack["id"]
            assert retrieved["contextPack"]["workspaceId"] == workspace_id
            assert retrieved["contextPack"]["fileCount"] == pack["summary"]["fileCount"]

            cpack_resp = client2.get(
                f"/api/v1/workspaces/{workspace_id}/context-packs/{pack['id']}"
            )
            assert cpack_resp.status_code == 200
            assert cpack_resp.json()["id"] == pack["id"]
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_sql_repos_work_without_migrations_when_tables_already_exist() -> None:
    db_url, db_path = _temp_db()
    try:
        from mensura_core.persistence.database import (
            create_persistence_engine,
            create_session_factory,
        )
        from mensura_core.persistence.models import Base

        engine = create_persistence_engine(db_url)
        Base.metadata.create_all(engine)
        sf = create_session_factory(engine)

        from mensura_core.persistence.repositories.core import SqlCoreRepository

        repo = SqlCoreRepository(sf)
        from datetime import datetime

        from mensura_core.models import Workspace

        ws = Workspace(
            id=uuid4(),
            name="test",
            root_path="/tmp/test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        repo.add_workspace(ws)
        found = repo.get_workspace(ws.id)
        assert found is not None
        assert found.name == "test"

        listed = repo.list_workspaces()
        assert len(listed) == 1
        engine.dispose()
    finally:
        try:
            Path(db_path).unlink(missing_ok=True)
            Path(db_path + "-wal").unlink(missing_ok=True)
            Path(db_path + "-shm").unlink(missing_ok=True)
        except OSError:
            pass
