"""Installments and fixed payments: created from a message, listed and cancelled in /fijos."""

from datetime import UTC, datetime

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from asistente.bot.handlers.finance import entries as finance_entries
from asistente.bot.handlers.recurring import keyboards, views
from asistente.bot.handlers.recurring.callbacks import RecurringCallback
from asistente.bot.ui import edit_or_send
from asistente.config import Settings
from asistente.finance.recurring import RecurringRequest
from asistente.finance.recurring_service import RecurringPaymentService
from asistente.users.models import User


async def create(
    message: Message,
    request: RecurringRequest,
    recurring: RecurringPaymentService,
    user: User,
    settings: Settings,
) -> None:
    """Register today's charge (its usual card) and say what comes next."""
    registered = await recurring.register(user, request, now=message.date)
    if registered.transaction is not None:
        await finance_entries.answer_registered(message, registered.transaction, settings.tz)
    today = message.date.astimezone(settings.tz).date()
    await message.answer(views.created(registered, settings.tz, today=today))


async def list_payments(
    message: Message, recurring: RecurringPaymentService, user: User, settings: Settings
) -> None:
    payments = await recurring.active(user)
    today = message.date.astimezone(settings.tz).date()
    await message.answer(
        views.payment_list(payments, settings.tz, today=today),
        reply_markup=keyboards.listed(payments),
    )


async def cancel(
    callback: CallbackQuery,
    callback_data: RecurringCallback,
    bot: Bot,
    recurring: RecurringPaymentService,
    user: User,
    settings: Settings,
) -> None:
    await recurring.cancel(user, callback_data.payment_id)
    payments = await recurring.active(user)
    today = datetime.now(UTC).astimezone(settings.tz).date()
    text = views.payment_list(payments, settings.tz, today=today)
    await edit_or_send(callback, bot, text, keyboards.listed(payments))
    await callback.answer("Dado de baja")


def build_router() -> Router:
    router = Router(name="recurring")
    router.message.register(list_payments, Command("fijos"))
    router.callback_query.register(cancel, RecurringCallback.filter())
    return router
