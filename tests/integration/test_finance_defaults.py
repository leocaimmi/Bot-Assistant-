from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.finance.defaults import DEFAULT_ACCOUNTS, DEFAULT_CATEGORIES, seed_defaults
from asistente.finance.models import Account, Category, CategoryKeyword
from asistente.users.models import User


async def _count(session: AsyncSession, model: type[object]) -> int:
    return await session.scalar(select(func.count()).select_from(model)) or 0


async def test_seeds_categories_keywords_and_accounts(session: AsyncSession, user: User) -> None:
    assert await _count(session, Category) == len(DEFAULT_CATEGORIES)
    assert await _count(session, Account) == len(DEFAULT_ACCOUNTS)

    default_accounts = list(await session.scalars(select(Account).where(Account.is_default)))
    assert [account.name for account in default_accounts] == ["Mercado Pago"]

    nafta = await session.scalar(
        select(Category.name)
        .join(CategoryKeyword, CategoryKeyword.category_id == Category.id)
        .where(CategoryKeyword.keyword == "nafta")
    )
    assert nafta == "Transporte"


async def test_is_idempotent(session: AsyncSession, user: User) -> None:
    keywords_before = await _count(session, CategoryKeyword)

    await seed_defaults(session, user)

    assert await _count(session, Category) == len(DEFAULT_CATEGORIES)
    assert await _count(session, Account) == len(DEFAULT_ACCOUNTS)
    assert await _count(session, CategoryKeyword) == keywords_before


async def test_keeps_keywords_the_user_moved(session: AsyncSession, user: User) -> None:
    gym = await session.scalar(select(Category).where(Category.name == "Gimnasio"))
    keyword = await session.scalar(
        select(CategoryKeyword).where(CategoryKeyword.keyword == "nafta")
    )
    assert gym is not None and keyword is not None
    keyword.category_id = gym.id
    await session.flush()

    await seed_defaults(session, user)

    owners = list(
        await session.scalars(
            select(CategoryKeyword.category_id).where(CategoryKeyword.keyword == "nafta")
        )
    )
    assert owners == [gym.id]
