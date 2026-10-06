from datetime import UTC, date, datetime, timedelta

import pytest

from asistente.finance.service import (
    AmountChange,
    CategoryChange,
    DayChange,
    FinanceService,
    MissingTargetError,
    NoMatchingTransactionError,
)
from asistente.users.models import User

NOW = datetime(2026, 10, 5, 17, 30, tzinfo=UTC)
TODAY = date(2026, 10, 5)


async def test_finds_the_most_recent_match(finance: FinanceService, user: User) -> None:
    older = await finance.register(user, "uber 2000", now=NOW - timedelta(days=2))
    newer = await finance.register(user, "uber 2000", now=NOW)
    await finance.register(user, "sube 2000", now=NOW + timedelta(minutes=1))

    found = await finance.find_by_text(user, "uber 2000", today=TODAY)

    assert found.id == newer.id != older.id


async def test_filters_by_amount_day_and_category(finance: FinanceService, user: User) -> None:
    yesterday = await finance.register(user, "uber 1500 ayer", now=NOW)
    today = await finance.register(user, "uber 2000", now=NOW)

    assert (await finance.find_by_text(user, "uber 1500", today=TODAY)).id == yesterday.id
    assert (await finance.find_by_text(user, "el uber de ayer", today=TODAY)).id == yesterday.id
    assert (await finance.find_by_text(user, "transporte 2000", today=TODAY)).id == today.id


async def test_latest(finance: FinanceService, user: User) -> None:
    await finance.register(user, "uber 2000", now=NOW)
    last = await finance.register(user, "gym 47.000", now=NOW + timedelta(minutes=5))

    assert (await finance.find_by_text(user, "el último", today=TODAY)).id == last.id


async def test_errors(finance: FinanceService, user: User) -> None:
    await finance.register(user, "uber 2000", now=NOW)

    with pytest.raises(NoMatchingTransactionError):
        await finance.find_by_text(user, "uber 9999", today=TODAY)
    with pytest.raises(MissingTargetError):
        await finance.find_by_text(user, "", today=TODAY)


async def test_resolve_and_apply_changes(finance: FinanceService, user: User) -> None:
    transaction = await finance.register(user, "uber 2000", now=NOW)

    amount = await finance.resolve_change(user, "2.500", today=TODAY)
    category = await finance.resolve_change(user, "Comida", today=TODAY)
    day = await finance.resolve_change(user, "ayer", today=TODAY)

    assert amount == AmountChange(250_000)
    assert isinstance(category, CategoryChange) and category.category.name == "Comida"
    assert day == DayChange(date(2026, 10, 4))
    assert await finance.resolve_change(user, "cualquier cosa", today=TODAY) is None

    for change in (amount, category, day):
        assert change is not None
        updated = await finance.apply_change(user, transaction.id, change)
    assert updated.amount_cents == 250_000
    assert updated.category.name == "Comida"
