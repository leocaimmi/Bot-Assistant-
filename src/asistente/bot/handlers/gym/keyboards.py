from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from asistente.bot.handlers.gym.callbacks import (
    GymDayCallback,
    GymEditConfirmCallback,
    GymEntryAction,
    GymEntryCallback,
    GymUndoCallback,
)
from asistente.gym.models import Workout, WorkoutEntry
from asistente.gym.service import LoggedWorkout


def logged_actions(logged: LoggedWorkout) -> InlineKeyboardMarkup:
    """Undo what was just logged, or open the day to correct an exercise."""
    ids = [entry.id for entry in logged.entries]
    builder = InlineKeyboardBuilder()
    builder.button(
        text="↩️ Deshacer", callback_data=GymUndoCallback(first_id=min(ids), last_id=max(ids))
    )
    builder.button(text="✏️ Editar", callback_data=GymDayCallback.of(logged.day))
    return builder.as_markup()


def day_entries(workout: Workout | None) -> InlineKeyboardMarkup | None:
    """A button per exercise, numbered like the list."""
    if workout is None or not workout.entries:
        return None
    builder = InlineKeyboardBuilder()
    for number, entry in enumerate(workout.entries, start=1):
        builder.button(
            text=f"✏️ {number}",
            callback_data=GymEntryCallback(action=GymEntryAction.OPEN, entry_id=entry.id),
        )
    builder.adjust(5)
    return builder.as_markup()


def entry_actions(entry: WorkoutEntry) -> InlineKeyboardMarkup:
    """Requires ``entry.workout`` loaded."""
    builder = InlineKeyboardBuilder()
    for text, action in (("✏️ Corregir", GymEntryAction.EDIT), ("🗑 Borrar", GymEntryAction.DELETE)):
        builder.button(text=text, callback_data=GymEntryCallback(action=action, entry_id=entry.id))
    builder.button(text="« Volver al día", callback_data=GymDayCallback.of(entry.workout.day))
    builder.adjust(2, 1)
    return builder.as_markup()


def confirm_edit(token: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Aplicar", callback_data=GymEditConfirmCallback(apply=True, token=token))
    builder.button(
        text="✖️ Cancelar", callback_data=GymEditConfirmCallback(apply=False, token=token)
    )
    return builder.as_markup()
