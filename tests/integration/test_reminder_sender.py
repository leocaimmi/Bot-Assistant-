import asyncio
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
)
from aiogram.methods import SendMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.handlers.reminders import views
from asistente.bot.reminder_sender import run_reminders, send_due_reminders
from asistente.reminders.parser import parse_reminder
from asistente.reminders.service import ReminderService
from asistente.users.service import UserService
from tests.factories import ALLOWED_USER_ID, BUENOS_AIRES
from tests.harness import BotHarness

# Monday 5 October 2026, 10:00 in Buenos Aires.
NOW = datetime(2026, 10, 5, 10, 0, tzinfo=BUENOS_AIRES)


async def _create(session_factory: async_sessionmaker[AsyncSession], message: str) -> None:
    async with session_factory() as session, session.begin():
        user, _ = await UserService(session).get_or_create(ALLOWED_USER_ID)
        parsed = parse_reminder(message, NOW, BUENOS_AIRES)
        assert parsed is not None
        await ReminderService(session).create(user, parsed, now=NOW)


async def _send(harness: BotHarness, session_factory: Any, now: datetime) -> int:
    return await send_due_reminders(harness.bot, session_factory, BUENOS_AIRES, now)


async def test_sends_a_due_reminder_once(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _create(session_factory, "recordame en 20 minutos sacar la ropa")
    due = NOW + timedelta(minutes=20)

    assert await _send(harness, session_factory, NOW) == 0
    assert await _send(harness, session_factory, due) == 1
    assert harness.last_reply == "⏰ <b>Sacar la ropa</b>"
    request = harness.session.requests[-1]
    assert isinstance(request, SendMessage)
    assert request.chat_id == ALLOWED_USER_ID
    assert not request.disable_notification  # it arrives as a push notification
    assert await _send(harness, session_factory, due) == 0


async def test_a_late_reminder_says_when_it_was_due(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _create(session_factory, "recordame en 20 minutos sacar la ropa")

    await _send(harness, session_factory, NOW + timedelta(hours=3))

    assert "Era para hoy a las 10:20: el bot estaba apagado." in harness.last_reply


async def test_done_and_snooze_buttons(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _create(session_factory, "recordame todos los días a las 11 tomar agua")
    await _send(harness, session_factory, NOW + timedelta(hours=1))

    await harness.click(harness.button("10 min"))
    assert "Te lo vuelvo a recordar" in harness.last_reply

    await harness.click(harness.button("Listo"))
    assert harness.last_reply == "✅ <s>Tomar agua</s>"


async def test_a_blocked_bot_does_not_retry_forever(
    harness: BotHarness,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def blocked(*_args: object, **_kwargs: object) -> None:
        raise TelegramForbiddenError(
            method=SendMessage(chat_id=ALLOWED_USER_ID, text="x"),
            message="Forbidden: bot was blocked by the user",
        )

    monkeypatch.setattr(harness.bot, "send_message", blocked)
    await _create(session_factory, "recordame en 20 minutos sacar la ropa")
    due = NOW + timedelta(minutes=20)

    assert await _send(harness, session_factory, due) == 0
    monkeypatch.undo()
    assert await _send(harness, session_factory, due) == 0  # it was not left pending


async def test_the_loop_survives_errors(
    harness: BotHarness, caplog: pytest.LogCaptureFixture
) -> None:
    def broken_factory() -> AsyncSession:
        raise RuntimeError("database down")

    task = asyncio.create_task(
        run_reminders(harness.bot, broken_factory, BUENOS_AIRES, every=0)  # type: ignore[arg-type]
    )
    await asyncio.sleep(0.05)
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

    assert "Could not send the due reminders" in caplog.text
    assert task.cancelled()


def _failing(error: Exception) -> object:
    async def send(*_args: object, **_kwargs: object) -> None:
        raise error

    return send


def _telegram(kind: type[Exception]) -> Exception:
    return kind(method=SendMessage(chat_id=ALLOWED_USER_ID, text="x"), message="error")  # type: ignore[call-arg]


async def test_a_network_failure_keeps_the_reminder_for_the_next_round(
    harness: BotHarness,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _create(session_factory, "recordame en 20 minutos sacar la ropa")
    due = NOW + timedelta(minutes=20)
    monkeypatch.setattr(harness.bot, "send_message", _failing(_telegram(TelegramNetworkError)))

    assert await _send(harness, session_factory, due) == 0
    monkeypatch.undo()
    assert await _send(harness, session_factory, due) == 1


async def test_a_refused_message_is_not_retried(
    harness: BotHarness,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _create(session_factory, "recordame en 20 minutos sacar la ropa")
    due = NOW + timedelta(minutes=20)
    monkeypatch.setattr(harness.bot, "send_message", _failing(_telegram(TelegramBadRequest)))

    assert await _send(harness, session_factory, due) == 0
    monkeypatch.undo()
    assert await _send(harness, session_factory, due) == 0


async def test_a_broken_reminder_never_blocks_the_others(
    harness: BotHarness,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _create(session_factory, "recordame en 20 minutos romper todo")
    await _create(session_factory, "recordame en 30 minutos sacar la ropa")
    real_fired = views.fired

    def fired(reminder: object, *args: object, **kwargs: object) -> str:
        if "romper" in getattr(reminder, "text", ""):
            raise ValueError("unexpected")
        return real_fired(reminder, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(views, "fired", fired)
    due = NOW + timedelta(minutes=30)

    assert await _send(harness, session_factory, due) == 1
    assert harness.last_reply == "⏰ <b>Sacar la ropa</b>"
    assert await _send(harness, session_factory, due) == 0  # the broken one was turned off
