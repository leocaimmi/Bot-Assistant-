"""Callback data of the reminder buttons, validated when a button is pressed."""

from enum import StrEnum
from typing import Annotated

from aiogram.filters.callback_data import CallbackData
from pydantic import Field


class ReminderAction(StrEnum):
    DONE = "done"
    SNOOZE = "snooze"
    DELETE = "delete"
    DELETE_LISTED = "delete_listed"  # from /recordatorios: shows the list again


class ReminderCallback(CallbackData, prefix="rem"):
    action: ReminderAction
    reminder_id: Annotated[int, Field(ge=1)]
