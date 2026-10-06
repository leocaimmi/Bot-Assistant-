"""Sends the reminders that are due (one round of the scheduler, see ``bot.scheduler``).

Each reminder is sent in its own database transaction and marked as sent only after
Telegram accepts it, so a crash or a network error never loses one (at worst it is sent
twice). It is a normal Telegram message, so the phone shows it as a push notification.

A round handles at most ``DUE_BATCH`` reminders. A reminder Telegram refuses for good,
or one that fails in an unexpected way, is not retried, so it can never block the others.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.handlers.reminders import keyboards, views
from asistente.reminders.service import ReminderService

logger = logging.getLogger(__name__)

# Later than this, the message says when it was due (the bot was off).
LATE_AFTER = timedelta(minutes=5)

# Refused for good (bot blocked, chat gone): sending again would fail the same way.
_REFUSED = (TelegramForbiddenError, TelegramBadRequest)
# Failing for now (network, Telegram, a busy database): the reminder stays due.
_TEMPORARY = (TelegramNetworkError, TelegramRetryAfter, TelegramServerError, SQLAlchemyError)

SessionFactory = async_sessionmaker[AsyncSession]


async def send_due_reminders(
    bot: Bot, session_factory: SessionFactory, tz: ZoneInfo, now: datetime
) -> int:
    """Send every reminder due at ``now``; returns how many reached Telegram."""
    async with session_factory() as session:
        due_ids = await ReminderService(session).due_ids(now)
    sent = 0
    for reminder_id in due_ids:
        try:
            sent += await _send(bot, session_factory, tz, now, reminder_id)
        except _TEMPORARY:
            logger.warning("Reminders paused until the next round: Telegram or the DB failed")
            break
        except Exception:
            logger.exception("Reminder %s failed and was turned off", reminder_id)
            async with session_factory() as session, session.begin():
                await ReminderService(session).turn_off(reminder_id)
    return sent


async def _send(
    bot: Bot, session_factory: SessionFactory, tz: ZoneInfo, now: datetime, reminder_id: int
) -> int:
    async with session_factory() as session, session.begin():
        service = ReminderService(session)
        due = await service.claim(reminder_id, now)
        if due is None:  # deleted or sent in the meantime
            return 0
        late = now - due.reminder.next_run_at > LATE_AFTER
        try:
            await bot.send_message(
                due.chat_id,
                views.fired(due.reminder, tz, now=now, late=late),
                reply_markup=keyboards.fired(due.reminder.id),
            )
        except _REFUSED:
            logger.warning("Reminder %s not sent: Telegram refused it", reminder_id)
            await service.advance(due.reminder, now)
            return 0
        await service.advance(due.reminder, now)
        return 1
