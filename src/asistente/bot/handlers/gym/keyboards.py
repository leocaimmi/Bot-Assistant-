from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from asistente.bot.handlers.gym.callbacks import GymEntryCallback, GymUndoCallback
from asistente.gym.models import Workout
from asistente.gym.service import LoggedWorkout


def undo(logged: LoggedWorkout) -> InlineKeyboardMarkup:
    ids = [entry.id for entry in logged.entries]
    builder = InlineKeyboardBuilder()
    builder.button(
        text="↩️ Deshacer", callback_data=GymUndoCallback(first_id=min(ids), last_id=max(ids))
    )
    return builder.as_markup()


def day_entries(workout: Workout | None) -> InlineKeyboardMarkup | None:
    if workout is None or not workout.entries:
        return None
    builder = InlineKeyboardBuilder()
    for number, entry in enumerate(workout.entries, start=1):
        builder.button(text=f"🗑 {number}", callback_data=GymEntryCallback(entry_id=entry.id))
    builder.adjust(5)
    return builder.as_markup()
