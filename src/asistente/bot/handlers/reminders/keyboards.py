from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from asistente.bot.handlers.reminders.callbacks import ReminderAction, ReminderCallback


def created(reminder_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🗑 Borrar",
        callback_data=ReminderCallback(action=ReminderAction.DELETE, reminder_id=reminder_id),
    )
    return builder.as_markup()
