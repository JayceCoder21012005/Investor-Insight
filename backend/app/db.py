"""Engine, session dependency and migration helper."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlmodel import Session

from app.config import Settings

ROOT = Path(__file__).resolve().parent.parent
_engine: Engine | None = None


def normalize_url(url: str) -> str:
    """Neon gives postgresql://...; SQLAlchemy needs the psycopg 3 driver spelled out."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def make_engine(url: str) -> Engine:
    url = normalize_url(url)
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # SQLite ignores foreign keys unless asked
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine
    return create_engine(
        url,
        pool_pre_ping=True,  # Neon compute may scale to zero
        pool_size=5, max_overflow=5, pool_recycle=300,
        connect_args={"prepare_threshold": None},  # pooler runs PgBouncer in transaction mode
    )


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = make_engine(Settings().database_url)
    return _engine


def set_engine(engine: Engine | None) -> None:
    """Tests and the app factory inject an engine here."""
    global _engine
    _engine = engine


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def run_migrations(url: str) -> None:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")
