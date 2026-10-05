"""Callback data of the finance buttons (max 64 bytes each).

Values are validated when a button is pressed: anything out of range (e.g. data forged by
a modified client) fails the filter and ends in the fallback "button not available".
"""

from enum import StrEnum
from typing import Annotated, Self

from aiogram.filters.callback_data import CallbackData
from pydantic import Field, model_validator

from asistente.core.dates import MAX_YEAR, MIN_YEAR

Id = Annotated[int, Field(ge=1)]
Year = Annotated[int, Field(ge=MIN_YEAR, le=MAX_YEAR)]
Month = Annotated[int, Field(ge=1, le=12)]


class TxAction(StrEnum):
    OPEN = "open"  # show the card as a new message (from a list)
    BACK = "back"  # card with the short keyboard
    EDIT = "edit"  # card with every editable field
    AMOUNT = "amount"
    DESCRIPTION = "desc"
    DAY = "day"
    CATEGORY = "cat"
    ACCOUNT = "acc"
    TOGGLE_KIND = "kind"
    DELETE = "del"
    CONFIRM_DELETE = "delok"


class TxCallback(CallbackData, prefix="tx"):
    action: TxAction
    tx_id: Id


class TxCategoryCallback(CallbackData, prefix="txc"):
    tx_id: Id
    category_id: Id


class TxAccountCallback(CallbackData, prefix="txa"):
    tx_id: Id
    account_id: Id


class TxPageCallback(CallbackData, prefix="txp"):
    page: Annotated[int, Field(ge=0)]
    # Both 0 means "no month filter".
    year: Annotated[int, Field(ge=0, le=MAX_YEAR)] = 0
    month: Annotated[int, Field(ge=0, le=12)] = 0

    @model_validator(mode="after")
    def _month_is_complete(self) -> Self:
        no_filter = self.year == 0 and self.month == 0
        if not no_filter and (self.year < MIN_YEAR or self.month == 0):
            raise ValueError("invalid month filter")
        return self

    @property
    def period(self) -> tuple[int, int] | None:
        return (self.year, self.month) if self.year else None


class SummaryCallback(CallbackData, prefix="sum"):
    year: Year
    month: Month
