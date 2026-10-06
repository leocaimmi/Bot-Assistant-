"""Alembic environment: runs migrations with the same engine configuration as the bot."""

import asyncio
from logging.config import fileConfig
from typing import Any

from alembic import context
from alembic.autogenerate.api import AutogenContext
from sqlalchemy import Connection
from sqlalchemy.pool import NullPool

from asistente.config import DatabaseSettings
from asistente.db.engine import create_engine
from asistente.db.registry import Base
from asistente.db.types import UTCDateTime

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    # Tests inject the URL through attributes; everything else uses DATABASE_URL.
    url = config.attributes.get("database_url")
    if isinstance(url, str):
        return url
    return DatabaseSettings().database_url.get_secret_value()


def _render_item(type_: str, obj: Any, _autogen_context: AutogenContext) -> str | bool:
    # Migrations must not import app code that may change later: render plain SQLAlchemy types.
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # SQLite cannot ALTER most things: batch mode recreates tables instead.
        render_as_batch=True,
        render_item=_render_item,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

    if connection.dialect.name == "sqlite":
        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"Foreign key violations after migrating: {violations}")


async def run_migrations_online() -> None:
    # Foreign keys stay off while migrating (batch mode recreates tables and could cascade
    # deletes); integrity is verified afterwards with PRAGMA foreign_key_check.
    engine = create_engine(_database_url(), foreign_keys=False, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
