"""Async engine and session factory."""

from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

SQLITE_BUSY_TIMEOUT_MS = 5_000


def create_engine(url: str, *, foreign_keys: bool = True, **kwargs: Any) -> AsyncEngine:
    """Create the async engine. SQLite connections get consistent, safe PRAGMAs.

    ``foreign_keys=False`` is only meant for migrations, where SQLite batch operations
    recreate tables and enforcing foreign keys could cascade deletes.
    """
    # hide_parameters keeps user data (amounts, descriptions) out of error messages and logs.
    engine = create_async_engine(url, hide_parameters=True, **kwargs)
    if engine.dialect.name == "sqlite":
        _ensure_sqlite_directory(url)
        _configure_sqlite(engine, foreign_keys=foreign_keys)
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _ensure_sqlite_directory(url: str) -> None:
    database = make_url(url).database
    if database and database != ":memory:" and not database.startswith("file:"):
        Path(database).parent.mkdir(parents=True, exist_ok=True)


def _configure_sqlite(engine: AsyncEngine, *, foreign_keys: bool) -> None:
    foreign_keys_pragma = "PRAGMA foreign_keys=ON" if foreign_keys else "PRAGMA foreign_keys=OFF"

    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_connection: Any, _connection_record: Any) -> None:
        # Let SQLAlchemy drive transactions (see "begin" below) instead of the driver.
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        cursor.execute(foreign_keys_pragma)
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        cursor.close()

    @event.listens_for(engine.sync_engine, "begin")
    def _on_begin(connection: Any) -> None:
        # IMMEDIATE takes the write lock up front: concurrent updates wait (busy_timeout)
        # instead of failing with "database is locked" when a reader later writes.
        connection.exec_driver_sql("BEGIN IMMEDIATE")
