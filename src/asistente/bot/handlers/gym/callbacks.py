"""Callback data of the gym buttons, validated when a button is pressed."""

from typing import Annotated, Self

from aiogram.filters.callback_data import CallbackData
from pydantic import Field, model_validator

Id = Annotated[int, Field(ge=1)]


class GymUndoCallback(CallbackData, prefix="gu"):
    """Undo one logged message: its entries have consecutive ids."""

    first_id: Id
    last_id: Id

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.first_id > self.last_id:
            raise ValueError("first_id must not be greater than last_id")
        return self


class GymEntryCallback(CallbackData, prefix="ge"):
    """Delete one entry from the day view."""

    entry_id: Id
