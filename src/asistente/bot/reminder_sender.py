"""Sends the reminders that are due: a loop that runs next to long polling.

Each reminder is sent in its own database transaction and marked as sent only after
Telegram accepts it, so a crash or a network error never loses one (at worst it is sent
twice). It is a normal Telegram message, so the phone shows it as a push notification.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.handlers.reminders import keyboards, views
from asistente.reminders.service import ReminderService

logger = logging.getLogger(__name__)

CHECK_EVERY_SECONDS = 20
# Later than this, the message says when it was due (the bot was off).
LATE_AFTER = timedelta(minutes=5)


async def send_due_reminders(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession], tz: ZoneInfo, now: datetime
) -> int:
    """Send every reminder due at ``now``; returns how many reached Telegram."""
    async with session_factory() as session:
        due_ids = await ReminderService(session).due_ids(now)
    sent = 0
    for reminder_id in due_ids:
        async with session_factory() as session, session.begin():
            service = ReminderService(session)
            due = await service.claim(reminder_id, now)
            if due is None:  # deleted or sent in the meantime
                continue
            late = now - due.reminder.next_run_at > LATE_AFTER
            try:
                await bot.send_message(
                    due.chat_id,
                    views.fired(due.reminder, tz, now=now, late=late),
                    reply_markup=keyboards.fired(due.reminder.id),
                )
                sent += 1
            except TelegramForbiddenError:
                # The user blocked the bot: trying again would fail the same way.
                logger.warning("Reminder %s not sent: the bot is blocked", reminder_id)
            await service.advance(due.reminder, now)
    return sent


async def run_reminders(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
    *,
    every: float = CHECK_EVERY_SECONDS,
) -> None:
    """Check for due reminders until cancelled; a failed round is logged and retried."""
    while True:
        try:
            await send_due_reminders(bot, session_factory, tz, datetime.now(UTC))
        except Exception:
            logger.exception("Could not send the due reminders")
        await asyncio.sleep(every)
