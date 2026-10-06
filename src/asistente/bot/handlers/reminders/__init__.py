"""Reminders: created from a message (typed or spoken) and shown with a button to delete."""

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from asistente.bot.handlers.reminders import keyboards, views
from asistente.bot.handlers.reminders.callbacks import ReminderAction, ReminderCallback
from asistente.bot.ui import edit_or_send
from asistente.config import Settings
from asistente.reminders.models import Reminder
from asistente.reminders.parser import parse_reminder
from asistente.reminders.service import ReminderService
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


def build_router() -> Router:
    router = Router(name="reminders")
    router.callback_query.register(
        delete, ReminderCallback.filter(F.action == ReminderAction.DELETE)
    )
    return router
