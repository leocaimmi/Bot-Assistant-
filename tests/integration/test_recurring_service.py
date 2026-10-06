from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.finance.models import Transaction
from asistente.finance.recurring import parse_recurring
from asistente.finance.recurring_service import (
    MAX_ACTIVE_RECURRING,
    MAX_CATCH_UP,
    RecurringNotFoundError,
    RecurringPaymentService,
    TooManyRecurringError,
)
from asistente.users.models import User
from asistente.users.service import UserService
from tests.factories import BUENOS_AIRES

# Monday 5 October 2026, 10:00 in Buenos Aires.
NOW = datetime(2026, 10, 5, 10, 0, tzinfo=BUENOS_AIRES)


def _at(day: int, month: int, year: int = 2026) -> datetime:
    return datetime(year, month, day, 9, 0, tzinfo=BUENOS_AIRES)


@pytest.fixture
def recurring(session: AsyncSession) -> RecurringPaymentService:
    return RecurringPaymentService(session, BUENOS_AIRES)


async def _register(service: RecurringPaymentService, user: User, text: str):  # type: ignore[no-untyped-def]
    request = parse_recurring(text)
    assert request is not None, text
    return await service.register(user, request, now=NOW)


async def _descriptions(session: AsyncSession) -> list[tuple[str, int]]:
    rows = await session.execute(
        select(Transaction.description, Transaction.amount_cents).order_by(Transaction.id)
    )
    return [(description, cents) for description, cents in rows]


async def test_installments_start_now_and_continue_monthly(
    recurring: RecurringPaymentService, user: User
) -> None:
    registered = await _register(recurring, user, "zapatillas 10.000 cuota 1 de 9")

    assert registered.transaction is not None
    assert registered.transaction.description == "zapatillas (1/9)"
    assert registered.transaction.amount_cents == 1_000_000
    payment = registered.payment
    assert payment is not None
    assert (payment.next_number, payment.installments, payment.day_of_month) == (2, 9, 5)
    assert payment.next_run_at == _at(5, 11)
    assert payment.category.name == "Ropa"


async def test_the_purchase_day_sets_the_monthly_day(
    recurring: RecurringPaymentService, user: User
) -> None:
    registered = await _register(recurring, user, "zapatillas 10.000 cuota 1 de 9 15/08")

    assert registered.transaction is not None and registered.payment is not None
    assert registered.transaction.occurred_at.astimezone(BUENOS_AIRES).day == 15
    assert registered.payment.day_of_month == 15
    # The 2/9 of 15/09 already passed: it is due, so the scheduler registers it now.
    assert registered.payment.next_run_at == _at(15, 9)
    assert await recurring.due_ids(NOW) == [registered.payment.id]


async def test_the_total_is_split_with_the_extra_cents_first(
    recurring: RecurringPaymentService, user: User
) -> None:
    registered = await _register(recurring, user, "zapatillas 100.000 en 3 cuotas")

    assert registered.transaction is not None and registered.payment is not None
    assert registered.transaction.amount_cents == 3_333_334
    assert registered.payment.amount_cents == 3_333_333


async def test_the_last_installment_has_nothing_to_come(
    recurring: RecurringPaymentService, user: User
) -> None:
    registered = await _register(recurring, user, "zapatillas 10.000 cuota 9 de 9")

    assert registered.transaction is not None
    assert registered.transaction.description == "zapatillas (9/9)"
    assert registered.payment is None


async def test_a_fixed_payment_on_another_day_waits_for_it(
    session: AsyncSession, recurring: RecurringPaymentService, user: User
) -> None:
    registered = await _register(recurring, user, "alquiler 300.000 el 10 de cada mes")

    assert registered.transaction is None
    assert registered.payment is not None
    assert registered.payment.next_run_at == _at(10, 10)
    assert registered.payment.installments is None
    assert await _descriptions(session) == []  # nothing is registered before the day


async def test_charges_when_due_and_stops_after_the_last_installment(
    session: AsyncSession, recurring: RecurringPaymentService, user: User
) -> None:
    payment = (await _register(recurring, user, "zapatillas 10.000 cuota 7 de 9")).payment
    assert payment is not None

    assert await recurring.due_ids(_at(4, 11)) == []
    assert await recurring.due_ids(_at(5, 11)) == [payment.id]
    charged = await recurring.charge(payment.id, _at(5, 11))
    assert charged is not None and charged.chat_id == user.telegram_id
    assert [t.description for t in charged.transactions] == ["zapatillas (8/9)"]
    assert charged.transactions[0].occurred_at == _at(5, 11)
    assert payment.active and payment.next_run_at == _at(5, 12)

    # Off for months: the missed one is registered, then it is over.
    charged = await recurring.charge(payment.id, _at(1, 3, 2027))
    assert charged is not None
    assert [t.description for t in charged.transactions] == ["zapatillas (9/9)"]
    assert not payment.active
    assert await recurring.charge(payment.id, _at(1, 3, 2027)) is None
    assert [d for d, _ in await _descriptions(session)] == [
        "zapatillas (7/9)",
        "zapatillas (8/9)",
        "zapatillas (9/9)",
    ]


async def test_a_long_outage_is_caught_up_in_bounded_rounds(
    recurring: RecurringPaymentService, user: User
) -> None:
    payment = (await _register(recurring, user, "seguro del celu 5.000 todos los meses")).payment
    assert payment is not None
    much_later = _at(5, 1, 2028)  # 15 monthly charges are due

    first = await recurring.charge(payment.id, much_later)
    second = await recurring.charge(payment.id, much_later)

    assert first is not None and len(first.transactions) == MAX_CATCH_UP
    assert second is not None and len(second.transactions) == 15 - MAX_CATCH_UP
    assert payment.next_run_at == _at(5, 2, 2028)


async def test_cancel_stops_future_charges(
    session: AsyncSession, recurring: RecurringPaymentService, user: User
) -> None:
    payment = (await _register(recurring, user, "netflix 8.000 mensual")).payment
    assert payment is not None
    stranger, _ = await UserService(session).get_or_create(999)

    with pytest.raises(RecurringNotFoundError):
        await recurring.cancel(stranger, payment.id)
    await recurring.cancel(user, payment.id)

    assert await recurring.active(user) == []
    assert await recurring.due_ids(_at(5, 12)) == []
    with pytest.raises(RecurringNotFoundError):
        await recurring.cancel(user, payment.id)


async def test_limits_the_active_payments(recurring: RecurringPaymentService, user: User) -> None:
    for _ in range(MAX_ACTIVE_RECURRING):
        await _register(recurring, user, "algo 1.000 todos los meses")

    with pytest.raises(TooManyRecurringError):
        await _register(recurring, user, "otra cosa 1.000 todos los meses")
    # The last installment never adds a payment, so it is always allowed.
    assert (await _register(recurring, user, "zapatillas 1.000 cuota 9 de 9")).payment is None
