import logging
import os
from collections.abc import Callable
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.expanduser("~/.mensura/core.db")
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH}"
DEFAULT_BACKUP_DIR = os.path.expanduser("~/.mensura/backups")


# Explicit 5s busy wait: with WAL mode SQLite still serializes writers, and the single
# in-process job worker can briefly contend with a synchronous HTTP request on the same
# connection pool. Setting busy_timeout at the SQLite level (rather than relying on the
# pysqlite driver's default) makes the wait explicit and driver-independent.
SQLITE_BUSY_TIMEOUT_MS = 5000


def _configure_sqlite_pragmas(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    cursor.close()


def create_persistence_engine(database_url: str | None = None) -> Engine:
    url = database_url or os.environ.get("MENSURA_DATABASE_URL", DEFAULT_DATABASE_URL)
    db_path = Path(url.replace("sqlite:///", ""))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine_kwargs: dict = {}
    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(url, **engine_kwargs)

    if url.startswith("sqlite"):
        event.listen(engine, "connect", _configure_sqlite_pragmas)

    return engine


def create_session_factory(engine: Engine) -> Callable[[], Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def run_migrations(database_url: str | None = None) -> None:
    url = database_url or os.environ.get("MENSURA_DATABASE_URL", DEFAULT_DATABASE_URL)
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    if not (migrations_dir / "alembic.ini").exists():
        logger.warning(
            "Alembic configuration not found at %s; skipping migrations.", migrations_dir
        )
        return

    alembic_cfg = AlembicConfig(str(migrations_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    alembic_command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations applied successfully.")


def get_alembic_head() -> str | None:
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    ini_path = migrations_dir / "alembic.ini"
    if not ini_path.exists():
        return None
    config = AlembicConfig(str(ini_path))
    config.set_main_option("script_location", str(migrations_dir))
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    return heads[0] if heads else None


def extract_db_path(database_url: str | None = None) -> str:
    url = database_url or os.environ.get("MENSURA_DATABASE_URL", DEFAULT_DATABASE_URL)
    return url.replace("sqlite:///", "")
