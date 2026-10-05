"""Callback data of the finance buttons (max 64 bytes each, validated by aiogram)."""

from enum import StrEnum

from aiogram.filters.callback_data import CallbackData


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
    tx_id: int


class TxCategoryCallback(CallbackData, prefix="txc"):
    tx_id: int
    category_id: int


class TxAccountCallback(CallbackData, prefix="txa"):
    tx_id: int
    account_id: int


class TxPageCallback(CallbackData, prefix="txp"):
    page: int
    # 0 means "no month filter".
    year: int = 0
    month: int = 0
