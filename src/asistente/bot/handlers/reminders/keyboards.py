from collections.abc import Sequence

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from asistente.bot.handlers.reminders.callbacks import ReminderAction, ReminderCallback
from asistente.reminders.models import Reminder
from asistente.reminders.service import SNOOZE_MINUTES


def fired(reminder_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Listo",
        callback_data=ReminderCallback(action=ReminderAction.DONE, reminder_id=reminder_id),
    )
    builder.button(
        text=f"⏳ {SNOOZE_MINUTES} min",
        callback_data=ReminderCallback(action=ReminderAction.SNOOZE, reminder_id=reminder_id),
    )
    return builder.as_markup()


def created(reminder_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🗑 Borrar",
        callback_data=ReminderCallback(action=ReminderAction.DELETE, reminder_id=reminder_id),
    )
    return builder.as_markup()


def listed(reminders: Sequence[Reminder]) -> InlineKeyboardMarkup | None:
    if not reminders:
        return None
    builder = InlineKeyboardBuilder()
    for number, reminder in enumerate(reminders, start=1):
        action = ReminderAction.DELETE_LISTED
        builder.button(
            text=f"🗑 {number}",
            callback_data=ReminderCallback(action=action, reminder_id=reminder.id),
        )
    builder.adjust(5)
    return builder.as_markup()
