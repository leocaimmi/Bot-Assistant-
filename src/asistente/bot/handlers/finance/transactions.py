"""Listing, viewing, editing and deleting transactions."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, Message

from asistente.bot.handlers.finance import keyboards, views
from asistente.bot.handlers.finance.callbacks import (
    TxAccountCallback,
    TxAction,
    TxCallback,
    TxCategoryCallback,
    TxPageCallback,
)
from asistente.bot.handlers.finance.states import EditTransaction
from asistente.bot.ui import edit_or_send
from asistente.config import Settings
from asistente.core.dates import parse_day, parse_month
from asistente.core.money import parse_amount
from asistente.finance.models import Transaction
from asistente.finance.service import FinanceService
from asistente.users.models import User

UPDATED = "✏️ Movimiento actualizado"


# --- Lists -------------------------------------------------------------------------------


async def list_transactions(
    message: Message,
    command: CommandObject,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    month = None
    if command.args:
        today = message.date.astimezone(settings.tz).date()
        month = parse_month(command.args, today)
        if month is None:
            await message.answer(views.INVALID_MONTH)
            return
    page = await finance.page(user, 0, month=month)
    await message.answer(
        views.transactions_page(page, settings.tz, month),
        reply_markup=keyboards.transactions_page(page, month),
    )


async def change_page(
    callback: CallbackQuery,
    callback_data: TxPageCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    month = (callback_data.year, callback_data.month) if callback_data.year else None
    page = await finance.page(user, callback_data.page, month=month)
    await edit_or_send(
        callback,
        bot,
        views.transactions_page(page, settings.tz, month),
        keyboards.transactions_page(page, month),
    )
    await callback.answer()


# --- Transaction card --------------------------------------------------------------------


async def open_transaction(
    callback: CallbackQuery,
    callback_data: TxCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    transaction = await finance.get(user, callback_data.tx_id)
    await bot.send_message(
        callback.from_user.id,
        views.transaction_card(transaction, settings.tz),
        reply_markup=keyboards.transaction_actions(transaction.id),
    )
    await callback.answer()


async def show_actions(
    callback: CallbackQuery,
    callback_data: TxCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    transaction = await finance.get(user, callback_data.tx_id)
    await edit_or_send(
        callback,
        bot,
        views.transaction_card(transaction, settings.tz),
        keyboards.transaction_actions(transaction.id),
    )
    await callback.answer()


async def show_editor(
    callback: CallbackQuery,
    callback_data: TxCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    transaction = await finance.get(user, callback_data.tx_id)
    await edit_or_send(
        callback,
        bot,
        views.transaction_card(transaction, settings.tz),
        keyboards.transaction_editor(transaction),
    )
    await callback.answer()


async def show_category_picker(
    callback: CallbackQuery,
    callback_data: TxCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    transaction = await finance.get(user, callback_data.tx_id)
    categories = await finance.categories(user, transaction.kind)
    await edit_or_send(
        callback,
        bot,
        views.transaction_card(transaction, settings.tz),
        keyboards.category_picker(transaction.id, categories),
    )
    await callback.answer()


async def pick_category(
    callback: CallbackQuery,
    callback_data: TxCategoryCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    transaction = await finance.change_category(
        user, callback_data.tx_id, callback_data.category_id
    )
    await edit_or_send(
        callback,
        bot,
        views.transaction_card(transaction, settings.tz, title=UPDATED),
        keyboards.transaction_actions(transaction.id),
    )
    await callback.answer("Categoría actualizada")


async def show_account_picker(
    callback: CallbackQuery,
    callback_data: TxCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    transaction = await finance.get(user, callback_data.tx_id)
    accounts = await finance.accounts(user)
    await edit_or_send(
        callback,
        bot,
        views.transaction_card(transaction, settings.tz),
        keyboards.account_picker(transaction.id, accounts),
    )
    await callback.answer()


async def pick_account(
    callback: CallbackQuery,
    callback_data: TxAccountCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    transaction = await finance.change_account(user, callback_data.tx_id, callback_data.account_id)
    await edit_or_send(
        callback,
        bot,
        views.transaction_card(transaction, settings.tz, title=UPDATED),
        keyboards.transaction_actions(transaction.id),
    )
    await callback.answer("Cuenta actualizada")


async def toggle_kind(
    callback: CallbackQuery,
    callback_data: TxCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    transaction = await finance.toggle_kind(user, callback_data.tx_id)
    await edit_or_send(
        callback,
        bot,
        views.transaction_card(transaction, settings.tz, title=UPDATED),
        keyboards.transaction_editor(transaction),
    )
    await callback.answer(f"Ahora es un {views.KIND_LABELS[transaction.kind].lower()}")


async def ask_delete(
    callback: CallbackQuery,
    callback_data: TxCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    transaction = await finance.get(user, callback_data.tx_id)
    await edit_or_send(
        callback,
        bot,
        views.transaction_card(transaction, settings.tz, title="¿Borrar este movimiento?"),
        keyboards.delete_confirmation(transaction.id),
    )
    await callback.answer()


async def confirm_delete(
    callback: CallbackQuery,
    callback_data: TxCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
) -> None:
    await finance.delete(user, callback_data.tx_id)
    await edit_or_send(callback, bot, views.deleted(callback_data.tx_id), None)
    await callback.answer("Borrado")


# --- Conversation steps: ask for a value, then receive it ---------------------------------


async def ask_amount(
    callback: CallbackQuery,
    callback_data: TxCallback,
    state: FSMContext,
    bot: Bot,
    finance: FinanceService,
    user: User,
) -> None:
    await _ask(callback, callback_data, state, bot, finance, user, EditTransaction.amount)


async def ask_description(
    callback: CallbackQuery,
    callback_data: TxCallback,
    state: FSMContext,
    bot: Bot,
    finance: FinanceService,
    user: User,
) -> None:
    await _ask(callback, callback_data, state, bot, finance, user, EditTransaction.description)


async def ask_day(
    callback: CallbackQuery,
    callback_data: TxCallback,
    state: FSMContext,
    bot: Bot,
    finance: FinanceService,
    user: User,
) -> None:
    await _ask(callback, callback_data, state, bot, finance, user, EditTransaction.day)


async def receive_amount(
    message: Message, state: FSMContext, finance: FinanceService, user: User, settings: Settings
) -> None:
    try:
        cents = parse_amount(message.text or "")
    except ValueError:
        await message.answer(views.INVALID_AMOUNT)
        return
    transaction = await finance.change_amount(user, await _pop_tx_id(state), cents)
    await _reply_updated(message, transaction, settings)


async def receive_description(
    message: Message, state: FSMContext, finance: FinanceService, user: User, settings: Settings
) -> None:
    description = (message.text or "").strip()
    if not description:
        await message.answer(views.EMPTY_DESCRIPTION)
        return
    transaction = await finance.change_description(user, await _pop_tx_id(state), description)
    await _reply_updated(message, transaction, settings)


async def receive_day(
    message: Message, state: FSMContext, finance: FinanceService, user: User, settings: Settings
) -> None:
    day = parse_day(message.text or "", message.date.astimezone(settings.tz).date())
    if day is None:
        await message.answer(views.INVALID_DAY)
        return
    transaction = await finance.change_day(user, await _pop_tx_id(state), day)
    await _reply_updated(message, transaction, settings)


# --- Helpers -------------------------------------------------------------------------------


_PROMPTS = {
    EditTransaction.amount: views.ASK_AMOUNT,
    EditTransaction.description: views.ASK_DESCRIPTION,
    EditTransaction.day: views.ASK_DAY,
}


async def _ask(
    callback: CallbackQuery,
    callback_data: TxCallback,
    state: FSMContext,
    bot: Bot,
    finance: FinanceService,
    user: User,
    step: State,
) -> None:
    await finance.get(user, callback_data.tx_id)  # fail early if it no longer exists
    await state.set_state(step)
    await state.update_data(tx_id=callback_data.tx_id)
    await bot.send_message(callback.from_user.id, _PROMPTS[step])
    await callback.answer()


async def _pop_tx_id(state: FSMContext) -> int:
    """Transaction being edited; the step ends here even if the update later fails."""
    data = await state.get_data()
    await state.clear()
    return int(data["tx_id"])


async def _reply_updated(message: Message, transaction: Transaction, settings: Settings) -> None:
    await message.answer(
        views.transaction_card(transaction, settings.tz, title=UPDATED),
        reply_markup=keyboards.transaction_actions(transaction.id),
    )


def build_router() -> Router:
    router = Router(name="finance.transactions")
    router.message.register(list_transactions, Command("movimientos"))
    router.callback_query.register(change_page, TxPageCallback.filter())

    actions: dict[TxAction, Callable[..., Awaitable[Any]]] = {
        TxAction.OPEN: open_transaction,
        TxAction.BACK: show_actions,
        TxAction.EDIT: show_editor,
        TxAction.CATEGORY: show_category_picker,
        TxAction.ACCOUNT: show_account_picker,
        TxAction.TOGGLE_KIND: toggle_kind,
        TxAction.DELETE: ask_delete,
        TxAction.CONFIRM_DELETE: confirm_delete,
        TxAction.AMOUNT: ask_amount,
        TxAction.DESCRIPTION: ask_description,
        TxAction.DAY: ask_day,
    }
    for action, handler in actions.items():
        router.callback_query.register(handler, TxCallback.filter(F.action == action))
    router.callback_query.register(pick_category, TxCategoryCallback.filter())
    router.callback_query.register(pick_account, TxAccountCallback.filter())

    text_input = (F.text, ~F.text.startswith("/"))
    router.message.register(receive_amount, StateFilter(EditTransaction.amount), *text_input)
    router.message.register(
        receive_description, StateFilter(EditTransaction.description), *text_input
    )
    router.message.register(receive_day, StateFilter(EditTransaction.day), *text_input)
    return router
