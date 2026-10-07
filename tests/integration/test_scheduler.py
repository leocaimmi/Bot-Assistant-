import asyncio
from contextlib import suppress
from datetime import datetime
from typing import Any

import pytest
from aiogram.methods import SendMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.recurring_charger import charge_due_payments
from asistente.bot.scheduler import run_scheduler
from asistente.finance.defaults import seed_defaults
from asistente.finance.models import RecurringPayment, Transaction
from asistente.finance.recurring import parse_recurring
from asistente.finance.recurring_service import RecurringPaymentService
from asistente.users.service import UserService
from tests.factories import ALLOWED_USER_ID, BUENOS_AIRES
from tests.harness import BotHarness

# Monday 5 October 2026, 10:00 in Buenos Aires.
NOW = datetime(2026, 10, 5, 10, 0, tzinfo=BUENOS_AIRES)
NEXT_MONTH = datetime(2026, 11, 5, 9, 0, tzinfo=BUENOS_AIRES)


async def _register(session_factory: async_sessionmaker[AsyncSession], text: str) -> None:
    async with session_factory() as session, session.begin():
        user, _ = await UserService(session).get_or_create(ALLOWED_USER_ID)
        await seed_defaults(session, user)
        request = parse_recurring(text)
        assert request is not None
        await RecurringPaymentService(session, BUENOS_AIRES).register(user, request, now=NOW)


async def _descriptions(session_factory: async_sessionmaker[AsyncSession]) -> list[str]:
    async with session_factory() as session:
        query = select(Transaction.description).order_by(Transaction.id)
        return list(await session.scalars(query))


async def test_charges_due_payments_once_and_tells_quietly(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _register(session_factory, "zapatillas 10.000 cuota 1 de 9")

    assert await charge_due_payments(harness.bot, session_factory, BUENOS_AIRES, NOW) == 0
    assert await charge_due_payments(harness.bot, session_factory, BUENOS_AIRES, NEXT_MONTH) == 1
    assert await charge_due_payments(harness.bot, session_factory, BUENOS_AIRES, NEXT_MONTH) == 0

    assert await _descriptions(session_factory) == ["Zapatillas (1/9)", "Zapatillas (2/9)"]
    assert harness.last_reply == "🔁 Anoté <b>Zapatillas (2/9)</b>: $10.000 (05/11)"
    request = harness.session.requests[-1]
    assert isinstance(request, SendMessage)
    assert request.disable_notification  # no sound for an automatic charge


async def test_a_broken_payment_is_turned_off(
    harness: BotHarness,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _register(session_factory, "seguro del celu 5.000 todos los meses")

    async def broken(*_args: object, **_kwargs: object) -> None:
        raise ValueError("unexpected")

    monkeypatch.setattr(RecurringPaymentService, "charge", broken)
    assert await charge_due_payments(harness.bot, session_factory, BUENOS_AIRES, NEXT_MONTH) == 0
    monkeypatch.undo()

    async with session_factory() as session:
        payment = await session.scalar(select(RecurringPayment))
    assert payment is not None and not payment.active
    assert await charge_due_payments(harness.bot, session_factory, BUENOS_AIRES, NEXT_MONTH) == 0


async def test_the_loop_runs_every_job_and_survives_errors(
    harness: BotHarness, caplog: pytest.LogCaptureFixture
) -> None:
    calls: list[str] = []

    async def failing(*_args: Any) -> int:
        calls.append("failing")
        raise RuntimeError("database down")

    async def working(*_args: Any) -> int:
        calls.append("working")
        return 0

    task = asyncio.create_task(
        run_scheduler(harness.bot, None, BUENOS_AIRES, every=0, jobs=(failing, working))  # type: ignore[arg-type]
    )
    await asyncio.sleep(0.05)
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

    assert task.cancelled()
    assert "Scheduled job failing failed" in caplog.text
    assert calls[:4] == ["failing", "working", "failing", "working"]  # it keeps going
