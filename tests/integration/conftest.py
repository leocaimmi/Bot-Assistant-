from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from asistente.bot.app import build_dispatcher
from asistente.db.engine import create_engine, create_session_factory
from asistente.db.registry import Base
from asistente.finance.defaults import seed_defaults
from asistente.users.models import User
from asistente.users.service import UserService
from tests.factories import ALLOWED_USER_ID, make_settings
from tests.harness import BotHarness


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def user(session: AsyncSession) -> User:
    """The allowed user, registered and with the default finance data."""
    user, _ = await UserService(session).get_or_create(ALLOWED_USER_ID)
    await seed_defaults(session, user)
    return user


@pytest.fixture
def harness(session_factory: async_sessionmaker[AsyncSession]) -> BotHarness:
    settings = make_settings()
    return BotHarness(build_dispatcher(settings, session_factory))
