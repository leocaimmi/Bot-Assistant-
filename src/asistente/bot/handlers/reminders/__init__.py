"""Reminders: created from a message (typed or spoken), listed in /recordatorios."""

from datetime import UTC, datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from asistente.bot.handlers.reminders import keyboards, views
from asistente.bot.handlers.reminders.callbacks import ReminderAction, ReminderCallback
from asistente.bot.ui import edit_or_send
from asistente.config import Settings
from asistente.reminders.models import Reminder
from asistente.reminders.parser import parse_reminder
from asistente.reminders.service import (
    SNOOZE_MINUTES,
    ReminderNotFoundError,
    ReminderService,
)
from asistente.users.models import User


async def create_from_text(
    message: Message, text: str, reminders: ReminderService, user: User, settings: Settings
) -> bool:
    """Create the reminder in ``text``; ``False`` if the rules cannot read its timing."""
    parsed = parse_reminder(text, message.date, settings.tz)
    if parsed is None:
        return False
    reminder = await reminders.create(user, parsed, now=message.date)
    await answer_created(message, reminder, settings)
    return True


async def answer_created(message: Message, reminder: Reminder, settings: Settings) -> None:
    await message.answer(
        views.created(reminder, settings.tz, now=message.date),
        reply_markup=keyboards.created(reminder.id),
    )


async def list_reminders(
    message: Message, reminders: ReminderService, user: User, settings: Settings
) -> None:
    items = await reminders.active(user)
    await message.answer(
        views.reminder_list(items, settings.tz, now=message.date),
        reply_markup=keyboards.listed(items),
    )


async def delete_listed(
    callback: CallbackQuery,
    callback_data: ReminderCallback,
    bot: Bot,
    reminders: ReminderService,
    user: User,
    settings: Settings,
) -> None:
    await reminders.delete(user, callback_data.reminder_id)
    items = await reminders.active(user)
    text = views.reminder_list(items, settings.tz, now=datetime.now(UTC))
    await edit_or_send(callback, bot, text, keyboards.listed(items))
    await callback.answer("Borrado")


async def delete(
    callback: CallbackQuery,
    callback_data: ReminderCallback,
    bot: Bot,
    reminders: ReminderService,
    user: User,
) -> None:
    await reminders.delete(user, callback_data.reminder_id)
    await edit_or_send(callback, bot, views.DELETED, None)
    await callback.answer()


async def mark_done(
    callback: CallbackQuery,
    callback_data: ReminderCallback,
    bot: Bot,
    reminders: ReminderService,
    user: User,
) -> None:
    try:
        text = views.done(await reminders.get(user, callback_data.reminder_id))
    except ReminderNotFoundError:
        text = "✅ Listo"
    await edit_or_send(callback, bot, text, None)
    await callback.answer("¡Listo!")


async def snooze(
    callback: CallbackQuery,
    callback_data: ReminderCallback,
    bot: Bot,
    reminders: ReminderService,
    user: User,
    settings: Settings,
) -> None:
    copy = await reminders.snooze(user, callback_data.reminder_id, now=datetime.now(UTC))
    await edit_or_send(callback, bot, views.snoozed(copy, settings.tz), None)
    await callback.answer(f"Te aviso en {SNOOZE_MINUTES} minutos")


def build_router() -> Router:
    router = Router(name="reminders")
    router.message.register(list_reminders, Command("recordatorios"))
    router.callback_query.register(
        delete_listed, ReminderCallback.filter(F.action == ReminderAction.DELETE_LISTED)
    )
    router.callback_query.register(
        mark_done, ReminderCallback.filter(F.action == ReminderAction.DONE)
    )
    router.callback_query.register(
        snooze, ReminderCallback.filter(F.action == ReminderAction.SNOOZE)
    )
    router.callback_query.register(
        delete, ReminderCallback.filter(F.action == ReminderAction.DELETE)
    )
    return router
