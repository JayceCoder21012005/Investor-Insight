from alembic import context
from sqlalchemy import create_engine, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  (register tables on the metadata)
from app.config import Settings
from app.db import normalize_url

config = context.config
target_metadata = SQLModel.metadata


def _url() -> str:
    return normalize_url(config.get_main_option("sqlalchemy.url") or Settings().direct_database_url)


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
