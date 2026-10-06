"""Registers the installments and fixed payments that are due, and tells the user.

Each payment is charged in its own database transaction, committed before the notice is
sent: a lost notice never means a missing or a repeated charge. A payment that fails in
an unexpected way is turned off, so it is never retried forever.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.handlers.recurring import views
from asistente.finance.recurring_service import RecurringPaymentService

logger = logging.getLogger(__name__)


async def charge_due_payments(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession], tz: ZoneInfo, now: datetime
) -> int:
    """Register every payment due at ``now``; returns how many charges were registered."""
    async with session_factory() as session:
        due_ids = await RecurringPaymentService(session, tz).due_ids(now)
    registered = 0
    for payment_id in due_ids:
        try:
            async with session_factory() as session, session.begin():
                charged = await RecurringPaymentService(session, tz).charge(payment_id, now)
        except SQLAlchemyError:
            logger.warning("Payments paused until the next round: the database failed")
            break
        except Exception:
            logger.exception("Payment %s failed and was turned off", payment_id)
            async with session_factory() as session, session.begin():
                await RecurringPaymentService(session, tz).turn_off(payment_id)
            continue
        if charged is None or not charged.transactions:
            continue
        registered += len(charged.transactions)
        try:
            # Silent: an automatic charge is good to know, not worth a sound.
            await bot.send_message(
                charged.chat_id, views.charged(charged, tz), disable_notification=True
            )
        except TelegramAPIError:
            logger.warning("Payment %s registered; its notice could not be sent", payment_id)
    return registered
