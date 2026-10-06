from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.finance.defaults import seed_defaults
from asistente.finance.models import Category, TransactionKind
from asistente.finance.parser import MissingAmountError
from asistente.finance.service import (
    PAGE_SIZE,
    CategoryNotFoundError,
    FinanceService,
    InvalidAmountError,
    TransactionNotFoundError,
)
from asistente.users.models import User
from asistente.users.service import UserService
from tests.factories import BUENOS_AIRES, STRANGER_USER_ID

NOW = datetime(2026, 10, 5, 17, 30, tzinfo=UTC)  # 14:30 in Buenos Aires
EXPENSE = TransactionKind.EXPENSE
INCOME = TransactionKind.INCOME


async def _category_id(session: AsyncSession, user: User, name: str) -> int:
    category_id = await session.scalar(
        select(Category.id).where(Category.user_id == user.id, Category.name == name)
    )
    assert category_id is not None
    return category_id


@pytest.mark.parametrize(
    ("text", "kind", "category", "account", "cents", "description"),
    [
        ("uber 2000", EXPENSE, "Transporte", "Mercado Pago", 200_000, "uber"),
        ("gym 47.000", EXPENSE, "Gimnasio", "Mercado Pago", 4_700_000, "gym"),
        (
            "transferencia utn 200.000",
            INCOME,
            "Transferencias",
            "Mercado Pago",
            20_000_000,
            "transferencia utn",
        ),
        ("super 15.430,50 efectivo", EXPENSE, "Supermercado", "Efectivo", 1_543_050, "super"),
        ("Pedidos Ya 8500 mercado pago", EXPENSE, "Comida", "Mercado Pago", 850_000, "Pedidos Ya"),
        ("cosas varias 1500", EXPENSE, "Otros gastos", "Mercado Pago", 150_000, "cosas varias"),
        ("+ 50000 venta bici", INCOME, "Otros ingresos", "Mercado Pago", 5_000_000, "venta bici"),
        (
            "- 5000 transferencia a juan",
            EXPENSE,
            "Otros gastos",
            "Mercado Pago",
            500_000,
            "transferencia a juan",
        ),
        ("2000 efectivo", EXPENSE, "Otros gastos", "Efectivo", 200_000, ""),
    ],
)
async def test_register(
    finance: FinanceService,
    user: User,
    text: str,
    kind: TransactionKind,
    category: str,
    account: str,
    cents: int,
    description: str,
) -> None:
    transaction = await finance.register(user, text, now=NOW)

    assert transaction.kind is kind
    assert transaction.category.name == category
    assert transaction.account.name == account
    assert transaction.amount_cents == cents
    assert transaction.description == description
    assert transaction.occurred_at == NOW


async def test_register_with_day_keeps_local_time(finance: FinanceService, user: User) -> None:
    transaction = await finance.register(user, "nafta 30k ayer", now=NOW)

    local = transaction.occurred_at.astimezone(BUENOS_AIRES)
    assert (local.date(), local.hour, local.minute) == (date(2026, 10, 4), 14, 30)


async def test_register_requires_amount(finance: FinanceService, user: User) -> None:
    with pytest.raises(MissingAmountError):
        await finance.register(user, "hola", now=NOW)


async def test_change_category_also_changes_kind(
    session: AsyncSession, finance: FinanceService, user: User
) -> None:
    transaction = await finance.register(user, "uber 2000", now=NOW)

    updated = await finance.change_category(
        user, transaction.id, await _category_id(session, user, "Sueldo")
    )

    assert updated.category.name == "Sueldo"
    assert updated.kind is INCOME


async def test_toggle_kind_rematches_category(finance: FinanceService, user: User) -> None:
    transaction = await finance.register(user, "transferencia 1000", now=NOW)

    as_expense = await finance.toggle_kind(user, transaction.id)
    assert (as_expense.kind, as_expense.category.name) == (EXPENSE, "Otros gastos")

    as_income = await finance.toggle_kind(user, transaction.id)
    assert (as_income.kind, as_income.category.name) == (INCOME, "Transferencias")


async def test_change_amount_description_and_day(finance: FinanceService, user: User) -> None:
    transaction = await finance.register(user, "uber 2000", now=NOW)

    await finance.change_amount(user, transaction.id, 250_000)
    await finance.change_description(user, transaction.id, "  uber   al centro ")
    updated = await finance.change_day(user, transaction.id, date(2026, 9, 15))

    assert updated.amount_cents == 250_000
    assert updated.description == "uber al centro"
    local = updated.occurred_at.astimezone(BUENOS_AIRES)
    assert (local.date(), local.hour, local.minute) == (date(2026, 9, 15), 14, 30)


@pytest.mark.parametrize("cents", [0, -100])
async def test_change_amount_rejects_non_positive(
    finance: FinanceService, user: User, cents: int
) -> None:
    transaction = await finance.register(user, "uber 2000", now=NOW)

    with pytest.raises(InvalidAmountError):
        await finance.change_amount(user, transaction.id, cents)


async def test_delete(finance: FinanceService, user: User) -> None:
    transaction = await finance.register(user, "uber 2000", now=NOW)

    await finance.delete(user, transaction.id)

    with pytest.raises(TransactionNotFoundError):
        await finance.get(user, transaction.id)


async def test_cannot_reach_other_users_data(
    session: AsyncSession, finance: FinanceService, user: User
) -> None:
    stranger, _ = await UserService(session).get_or_create(STRANGER_USER_ID)
    await seed_defaults(session, stranger)
    foreign_transaction = await finance.register(stranger, "uber 2000", now=NOW)
    own_transaction = await finance.register(user, "uber 1000", now=NOW)

    with pytest.raises(TransactionNotFoundError):
        await finance.get(user, foreign_transaction.id)
    with pytest.raises(TransactionNotFoundError):
        await finance.delete(user, foreign_transaction.id)
    with pytest.raises(CategoryNotFoundError):
        await finance.change_category(
            user, own_transaction.id, await _category_id(session, stranger, "Gimnasio")
        )


async def test_page_groups_months_in_local_time(finance: FinanceService, user: User) -> None:
    # 01/10 02:00 UTC is still 30/09 in Buenos Aires.
    late_september = await finance.register(
        user, "uber 100", now=datetime(2026, 10, 1, 2, 0, tzinfo=UTC)
    )
    october = await finance.register(user, "uber 200", now=NOW)

    september_page = await finance.page(user, 0, month=(2026, 9))
    october_page = await finance.page(user, 0, month=(2026, 10))

    assert [t.id for t in september_page.items] == [late_september.id]
    assert [t.id for t in october_page.items] == [october.id]


async def test_pagination_newest_first(finance: FinanceService, user: User) -> None:
    created = [
        await finance.register(user, f"uber {100 + i}", now=NOW + timedelta(minutes=i))
        for i in range(PAGE_SIZE + 2)
    ]

    first = await finance.page(user, 0)
    second = await finance.page(user, 1)
    beyond = await finance.page(user, 99)

    assert first.items[0].id == created[-1].id
    assert (first.count, first.has_next, first.has_previous) == (2, True, False)
    assert len(second.items) == 2
    assert (second.has_next, second.has_previous) == (False, True)
    assert beyond.number == 1
