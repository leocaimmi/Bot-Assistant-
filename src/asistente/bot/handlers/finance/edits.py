"""Edits written or dictated in one sentence: shown as before → after, applied on OK.

A sentence can be misread (a transcription, a vague "el último"), so nothing changes
until the user confirms. The pending edit stays on the server; its buttons only carry a
random token, so an old or forged button cannot apply anything.
"""

import secrets
from datetime import date, time
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from aiogram import Bot, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pydantic import Field

from asistente.bot.handlers.finance import keyboards, views
from asistente.bot.ui import edit_or_send
from asistente.config import Settings
from asistente.finance.models import Transaction
from asistente.finance.service import (
    AccountChange,
    AmountChange,
    CategoryChange,
    Change,
    DayChange,
    DescriptionChange,
    FinanceService,
)
from asistente.users.models import User

PENDING_EDIT_KEY = "pending_edit"


class EditConfirmCallback(CallbackData, prefix="edc"):
    apply: bool
    token: Annotated[str, Field(pattern=r"^[0-9a-f]{8}$")]


async def propose(
    message: Message,
    transaction: Transaction,
    changes: list[Change],
    state: FSMContext,
    tz: ZoneInfo,
) -> None:
    """Show what would change and keep it until the user applies or discards it."""
    token = secrets.token_hex(4)
    await state.update_data({PENDING_EDIT_KEY: _pending(token, transaction.id, changes)})
    preview = views.change_preview(transaction, changes, tz)
    await message.answer(
        views.transaction_card(transaction, tz, title=f"✏️ ¿Aplico este cambio?\n{preview}"),
        reply_markup=_confirm_keyboard(token),
    )


async def resolve(
    callback: CallbackQuery,
    callback_data: EditConfirmCallback,
    state: FSMContext,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    data = await state.get_data()
    pending = data.get(PENDING_EDIT_KEY)
    await state.update_data({PENDING_EDIT_KEY: None})
    if not pending or pending.get("token") != callback_data.token:
        await callback.answer("Este cambio ya no está disponible.", show_alert=True)
        return
    if not callback_data.apply:
        await edit_or_send(callback, bot, "👌 Cambio descartado.", None)
        await callback.answer()
        return

    transaction_id = int(pending["tx_id"])
    if "amount_cents" in pending:
        await finance.change_amount(user, transaction_id, int(pending["amount_cents"]))
    if "category_id" in pending:
        await finance.change_category(user, transaction_id, int(pending["category_id"]))
    if "day" in pending:
        at = time.fromisoformat(pending["at"]) if pending.get("at") else None
        day = date.fromisoformat(pending["day"])
        await finance.change_day(user, transaction_id, day, at=at)
    if "description" in pending:
        await finance.change_description(user, transaction_id, str(pending["description"]))
    if "account_id" in pending:
        await finance.change_account(user, transaction_id, int(pending["account_id"]))

    transaction = await finance.get(user, transaction_id)
    await edit_or_send(
        callback,
        bot,
        views.transaction_card(transaction, settings.tz, title="✏️ Movimiento actualizado"),
        keyboards.transaction_actions(transaction_id),
    )
    await callback.answer("Cambios aplicados")


def _pending(token: str, transaction_id: int, changes: list[Change]) -> dict[str, Any]:
    pending: dict[str, Any] = {"token": token, "tx_id": transaction_id}
    for change in changes:
        match change:
            case AmountChange(cents):
                pending["amount_cents"] = cents
            case CategoryChange(category):
                pending["category_id"] = category.id
            case DayChange(day, at):
                pending["day"] = day.isoformat()
                pending["at"] = at.isoformat(timespec="minutes") if at is not None else None
            case DescriptionChange(description):
                pending["description"] = description
            case AccountChange(account):
                pending["account_id"] = account.id
    return pending


def _confirm_keyboard(token: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Aplicar", callback_data=EditConfirmCallback(apply=True, token=token))
    builder.button(text="✖️ Cancelar", callback_data=EditConfirmCallback(apply=False, token=token))
    return builder.as_markup()


def build_router() -> Router:
    router = Router(name="finance.edits")
    router.callback_query.register(resolve, EditConfirmCallback.filter())
    return router
