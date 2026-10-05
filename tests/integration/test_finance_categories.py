from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.finance.categories import (
    CategoryAlreadyExistsError,
    CategoryService,
    InvalidCategoryNameError,
    InvalidKeywordError,
    KeywordIsAccountAliasError,
    UnknownCategoryError,
)
from asistente.finance.models import TransactionKind
from asistente.finance.service import FinanceService
from asistente.users.models import User

NOW = datetime(2026, 10, 5, 17, 30, tzinfo=UTC)


@pytest.fixture
def categories(session: AsyncSession) -> CategoryService:
    return CategoryService(session)


async def test_moves_an_existing_keyword(
    categories: CategoryService, finance: FinanceService, user: User
) -> None:
    assignment = await categories.assign_keyword(user, "Nafta  Gimnasio")

    assert assignment.keyword == "nafta"
    assert assignment.category.name == "Gimnasio"
    assert assignment.previous is not None and assignment.previous.name == "Transporte"
    transaction = await finance.register(user, "nafta 30000", now=NOW)
    assert transaction.category.name == "Gimnasio"


async def test_teaches_a_new_multiword_keyword_to_a_multiword_category(
    categories: CategoryService, finance: FinanceService, user: User
) -> None:
    assignment = await categories.assign_keyword(user, "kiosco de barrio otros gastos")

    assert (assignment.keyword, assignment.category.name) == ("kiosco de barrio", "Otros gastos")
    assert assignment.previous is None
    transaction = await finance.register(user, "Kiosco de Barrio 900", now=NOW)
    assert transaction.category.name == "Otros gastos"


async def test_create_category_then_assign_keyword(
    categories: CategoryService, finance: FinanceService, user: User
) -> None:
    car = await categories.create(user, "🚙 auto")
    await categories.assign_keyword(user, "nafta auto")

    transaction = await finance.register(user, "nafta 30000", now=NOW)

    assert (car.name, car.emoji, car.kind) == ("Auto", "🚙", TransactionKind.EXPENSE)
    assert transaction.category.id == car.id


async def test_create_income_category(categories: CategoryService, user: User) -> None:
    scholarship = await categories.create(user, "ingreso Becas")

    assert scholarship.kind is TransactionKind.INCOME
    assert scholarship.emoji == "🏷️"


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("nafta", UnknownCategoryError),
        ("nafta vehiculo", UnknownCategoryError),
        ("una frase de muchas palabras transporte", InvalidKeywordError),
        ("efectivo transporte", KeywordIsAccountAliasError),
    ],
)
async def test_assign_keyword_errors(
    categories: CategoryService, user: User, text: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        await categories.assign_keyword(user, text)


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("transporte", CategoryAlreadyExistsError),
        ("🚗 Educacion", CategoryAlreadyExistsError),
        ("🚗", InvalidCategoryNameError),
        ("x" * 41, InvalidCategoryNameError),
    ],
)
async def test_create_category_errors(
    categories: CategoryService, user: User, text: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        await categories.create(user, text)


async def test_overview_lists_keywords(categories: CategoryService, user: User) -> None:
    overview = await categories.overview(user)

    transport = next(category for category in overview if category.name == "Transporte")
    assert "uber" in [keyword.keyword for keyword in transport.keywords]
