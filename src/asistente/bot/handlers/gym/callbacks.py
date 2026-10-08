"""Callback data of the gym buttons, validated when a button is pressed."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Self

from aiogram.filters.callback_data import CallbackData
from pydantic import Field, model_validator

from asistente.core.dates import MAX_YEAR, MIN_YEAR

Id = Annotated[int, Field(ge=1)]
DayNumber = Annotated[
    int, Field(ge=date(MIN_YEAR, 1, 1).toordinal(), le=date(MAX_YEAR, 12, 31).toordinal())
]


class GymUndoCallback(CallbackData, prefix="gu"):
    """Undo one logged message: its entries have consecutive ids."""

    first_id: Id
    last_id: Id

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.first_id > self.last_id:
            raise ValueError("first_id must not be greater than last_id")
        return self


class GymEntryAction(StrEnum):
    OPEN = "open"  # the exercise with its buttons
    EDIT = "edit"  # ask for the new sets, reps or weight
    DELETE = "del"


class GymEntryCallback(CallbackData, prefix="ge"):
    """One exercise of a workout."""

    action: GymEntryAction
    entry_id: Id


class GymDayCallback(CallbackData, prefix="gd"):
    """The workout of a day, with a button per exercise."""

    day_number: DayNumber  # date.toordinal(): short and always a valid date

    @classmethod
    def of(cls, day: date) -> Self:
        return cls(day_number=day.toordinal())

    @property
    def day(self) -> date:
        return date.fromordinal(self.day_number)
