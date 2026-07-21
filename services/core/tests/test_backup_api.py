import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from mensura_core.main import create_app


def _temp_db() -> tuple[str, str]:
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="mensura_backup_")
    os.close(fd)
    return f"sqlite:///{db_path}", db_path


def test_create_backup_succeeds(tmp_path: Path) -> None:
    db_url, db_path = _temp_db()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    try:
        old_env = os.environ.get("MENSURA_BACKUP_DIR")
        os.environ["MENSURA_BACKUP_DIR"] = str(backup_dir)
        try:
            with TestClient(
                create_app(
                    run_migrations_on_startup=True,
                    database_url=db_url,
                    use_sql=True,
                ),
            ) as client:
                resp = client.post("/api/v1/backups", json={"label": "my backup"})

                assert resp.status_code == 201
                data = resp.json()
                assert data["status"] == "completed"
                assert data["label"] == "my backup"
                assert len(data["sha256Hex"]) == 64
                assert data["fileSizeBytes"] > 0
                assert data["storagePath"].startswith("backup-")
                assert data["storagePath"].endswith(".db")
                assert resp.headers["Location"] == f"/api/v1/backups/{data['id']}"

                backup_file = backup_dir / data["storagePath"]
                assert backup_file.exists()

                resp2 = client.get(f"/api/v1/backups/{data['id']}")
                assert resp2.status_code == 200
                assert resp2.json() == data

                resp3 = client.get("/api/v1/backups")
                assert resp3.status_code == 200
                col = resp3.json()
                assert col["total"] == 1
                assert len(col["items"]) == 1
        finally:
            if old_env is not None:
                os.environ["MENSURA_BACKUP_DIR"] = old_env
            else:
                os.environ.pop("MENSURA_BACKUP_DIR", None)
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_create_backup_without_label(tmp_path: Path) -> None:
    db_url, db_path = _temp_db()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    try:
        old_env = os.environ.get("MENSURA_BACKUP_DIR")
        os.environ["MENSURA_BACKUP_DIR"] = str(backup_dir)
        try:
            with TestClient(
                create_app(
                    run_migrations_on_startup=True,
                    database_url=db_url,
                    use_sql=True,
                ),
            ) as client:
                resp = client.post("/api/v1/backups", json={})
                assert resp.status_code == 201
                assert resp.json()["label"] is None
        finally:
            if old_env is not None:
                os.environ["MENSURA_BACKUP_DIR"] = old_env
            else:
                os.environ.pop("MENSURA_BACKUP_DIR", None)
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_list_backups_empty(tmp_path: Path) -> None:
    db_url, db_path = _temp_db()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    try:
        old_env = os.environ.get("MENSURA_BACKUP_DIR")
        os.environ["MENSURA_BACKUP_DIR"] = str(backup_dir)
        try:
            with TestClient(
                create_app(
                    run_migrations_on_startup=True,
                    database_url=db_url,
                    use_sql=True,
                ),
            ) as client:
                resp = client.get("/api/v1/backups")
                assert resp.status_code == 200
                assert resp.json()["total"] == 0
                assert resp.json()["items"] == []
        finally:
            if old_env is not None:
                os.environ["MENSURA_BACKUP_DIR"] = old_env
            else:
                os.environ.pop("MENSURA_BACKUP_DIR", None)
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_get_backup_not_found(tmp_path: Path) -> None:
    db_url, db_path = _temp_db()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    try:
        old_env = os.environ.get("MENSURA_BACKUP_DIR")
        os.environ["MENSURA_BACKUP_DIR"] = str(backup_dir)
        try:
            with TestClient(
                create_app(
                    run_migrations_on_startup=True,
                    database_url=db_url,
                    use_sql=True,
                ),
            ) as client:
                resp = client.get(
                    "/api/v1/backups/00000000-0000-0000-0000-000000000000"
                )
                assert resp.status_code == 404
                assert (
                    resp.json()["type"]
                    == "urn:mensura:problem:backup-not-found"
                )
        finally:
            if old_env is not None:
                os.environ["MENSURA_BACKUP_DIR"] = old_env
            else:
                os.environ.pop("MENSURA_BACKUP_DIR", None)
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_restore_succeeds(tmp_path: Path) -> None:
    db_url, db_path = _temp_db()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    try:
        old_env = os.environ.get("MENSURA_BACKUP_DIR")
        os.environ["MENSURA_BACKUP_DIR"] = str(backup_dir)
        try:
            with TestClient(
                create_app(
                    run_migrations_on_startup=True,
                    database_url=db_url,
                    use_sql=True,
                ),
            ) as client:
                resp = client.post("/api/v1/backups", json={})
                backup_id = resp.json()["id"]

                resp2 = client.post(f"/api/v1/backups/{backup_id}/restore")
                assert resp2.status_code == 200
                assert "restart" in resp2.json()["message"].lower()
        finally:
            if old_env is not None:
                os.environ["MENSURA_BACKUP_DIR"] = old_env
            else:
                os.environ.pop("MENSURA_BACKUP_DIR", None)
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_restore_not_found(tmp_path: Path) -> None:
    db_url, db_path = _temp_db()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    try:
        old_env = os.environ.get("MENSURA_BACKUP_DIR")
        os.environ["MENSURA_BACKUP_DIR"] = str(backup_dir)
        try:
            with TestClient(
                create_app(
                    run_migrations_on_startup=True,
                    database_url=db_url,
                    use_sql=True,
                ),
            ) as client:
                resp = client.post(
                    "/api/v1/backups/00000000-0000-0000-0000-000000000000/restore"
                )
                assert resp.status_code == 404
                assert "backup-not-found" in resp.json()["type"]
        finally:
            if old_env is not None:
                os.environ["MENSURA_BACKUP_DIR"] = old_env
            else:
                os.environ.pop("MENSURA_BACKUP_DIR", None)
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_backup_artifact_survives_restart(tmp_path: Path) -> None:
    db_url, db_path = _temp_db()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    try:
        old_env = os.environ.get("MENSURA_BACKUP_DIR")
        os.environ["MENSURA_BACKUP_DIR"] = str(backup_dir)
        try:
            backup_id = None
            with TestClient(
                create_app(
                    run_migrations_on_startup=True,
                    database_url=db_url,
                    use_sql=True,
                ),
            ) as client:
                resp = client.post("/api/v1/backups", json={"label": "survival test"})
                assert resp.status_code == 201
                backup_id = resp.json()["id"]

            with TestClient(
                create_app(
                    run_migrations_on_startup=False,
                    database_url=db_url,
                    use_sql=True,
                ),
            ) as client2:
                resp = client2.get(f"/api/v1/backups/{backup_id}")
                assert resp.status_code == 200
                assert resp.json()["id"] == backup_id
                assert resp.json()["label"] == "survival test"

                resp2 = client2.get("/api/v1/backups")
                assert resp2.status_code == 200
                assert resp2.json()["total"] == 1
        finally:
            if old_env is not None:
                os.environ["MENSURA_BACKUP_DIR"] = old_env
            else:
                os.environ.pop("MENSURA_BACKUP_DIR", None)
    finally:
        Path(db_path).unlink(missing_ok=True)
