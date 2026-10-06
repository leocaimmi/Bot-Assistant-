"""Background jobs that run next to long polling: due reminders and automatic payments.

One round per minute, on the minute (12:00:01, 12:01:01...): reminders and payments are
set to whole minutes, so one at 12:00 goes out at 12:00:01. Each job handles a bounded
batch, a failing job never stops the others, and the loop always sleeps between rounds,
so it can never spin. No job uses the AI.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.recurring_charger import charge_due_payments
from asistente.bot.reminder_sender import send_due_reminders

logger = logging.getLogger(__name__)

CHECK_EVERY_SECONDS = 60
# Rounds run just after each minute starts, so a sleep that wakes a few milliseconds
# early never leaves something due at 12:00 for the 12:01 round.
ROUND_OFFSET_SECONDS = 1

Job = Callable[[Bot, async_sessionmaker[AsyncSession], ZoneInfo, datetime], Awaitable[int]]
JOBS: tuple[Job, ...] = (send_due_reminders, charge_due_payments)


async def run_scheduler(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    tz: ZoneInfo,
    *,
    every: float = CHECK_EVERY_SECONDS,
    jobs: Sequence[Job] = JOBS,
) -> None:
    """Run every job each round until cancelled (the first round runs right away)."""
    while True:
        now = datetime.now(UTC)
        for job in jobs:
            try:
                await job(bot, session_factory, tz, now)
            except Exception:
                logger.exception("Scheduled job %s failed", getattr(job, "__name__", job))
        await asyncio.sleep(seconds_until_next_round(datetime.now(UTC), every))


def seconds_until_next_round(now: datetime, every: float = CHECK_EVERY_SECONDS) -> float:
    """Wait until the next round, aligned to the clock: always more than 0, at most ``every``."""
    if every <= 0:
        return 0
    return every - (now.timestamp() - ROUND_OFFSET_SECONDS) % every
