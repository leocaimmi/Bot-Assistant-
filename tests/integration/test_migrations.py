import asyncio
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Connection, inspect

from asistente.db.engine import create_engine
from asistente.db.registry import Base

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    return config


def _schema_differences(database_url: str) -> list[object]:
    def compare(connection: Connection) -> list[object]:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        return list(compare_metadata(context, Base.metadata))

    async def run() -> list[object]:
        engine = create_engine(database_url)
        try:
            async with engine.connect() as connection:
                return await connection.run_sync(compare)
        finally:
            await engine.dispose()

    return asyncio.run(run())


def _table_names(database_url: str) -> set[str]:
    async def run() -> set[str]:
        engine = create_engine(database_url)
        try:
            async with engine.connect() as connection:
                return await connection.run_sync(lambda conn: set(inspect(conn).get_table_names()))
        finally:
            await engine.dispose()

    return asyncio.run(run())


def test_migrations_match_models_and_downgrade_cleanly(database_url: str) -> None:
    config = _alembic_config(database_url)

    command.upgrade(config, "head")
    assert _schema_differences(database_url) == []

    command.downgrade(config, "base")
    assert _table_names(database_url) <= {"alembic_version"}
