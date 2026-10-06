"""Callback data of the /fijos buttons, validated when a button is pressed."""

from typing import Annotated

from aiogram.filters.callback_data import CallbackData
from pydantic import Field


class RecurringCallback(CallbackData, prefix="rp"):
    """Cancel one installment plan or fixed payment from the /fijos list."""

    payment_id: Annotated[int, Field(ge=1)]
