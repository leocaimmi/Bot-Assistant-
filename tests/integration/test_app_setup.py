from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.app import set_up_existing_users
from asistente.finance.defaults import DEFAULT_CATEGORIES
from asistente.finance.models import Category
from asistente.users.service import UserService
from tests.factories import ALLOWED_USER_ID


async def test_startup_prepares_users_registered_before_a_module_existed(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session, session.begin():
        await UserService(session).get_or_create(ALLOWED_USER_ID)

    await set_up_existing_users(session_factory)
    await set_up_existing_users(session_factory)  # idempotent

    async with session_factory() as session:
        categories = await session.scalar(select(func.count()).select_from(Category))
    assert categories == len(DEFAULT_CATEGORIES)
