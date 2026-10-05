from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from asistente.bot.handlers.finance.callbacks import (
    TxAccountCallback,
    TxAction,
    TxCallback,
    TxCategoryCallback,
    TxPageCallback,
)
from asistente.finance.models import Account, Category, Transaction, TransactionKind
from asistente.finance.service import TransactionPage


def transaction_actions(transaction_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏷 Categoría", callback_data=_tx(TxAction.CATEGORY, transaction_id))
    builder.button(text="✏️ Editar", callback_data=_tx(TxAction.EDIT, transaction_id))
    builder.button(text="🗑 Borrar", callback_data=_tx(TxAction.DELETE, transaction_id))
    builder.adjust(3)
    return builder.as_markup()


def transaction_editor(transaction: Transaction) -> InlineKeyboardMarkup:
    is_expense = transaction.kind is TransactionKind.EXPENSE
    tx_id = transaction.id
    builder = InlineKeyboardBuilder()
    builder.button(text="💲 Importe", callback_data=_tx(TxAction.AMOUNT, tx_id))
    builder.button(text="📝 Descripción", callback_data=_tx(TxAction.DESCRIPTION, tx_id))
    builder.button(text="🏷 Categoría", callback_data=_tx(TxAction.CATEGORY, tx_id))
    builder.button(text="📅 Fecha", callback_data=_tx(TxAction.DAY, tx_id))
    builder.button(text="🏦 Cuenta", callback_data=_tx(TxAction.ACCOUNT, tx_id))
    builder.button(
        text="↔️ Es un ingreso" if is_expense else "↔️ Es un gasto",
        callback_data=_tx(TxAction.TOGGLE_KIND, tx_id),
    )
    builder.button(text="🗑 Borrar", callback_data=_tx(TxAction.DELETE, tx_id))
    builder.button(text="« Listo", callback_data=_tx(TxAction.BACK, tx_id))
    builder.adjust(2)
    return builder.as_markup()


def category_picker(transaction_id: int, categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=category.label,
            callback_data=TxCategoryCallback(tx_id=transaction_id, category_id=category.id),
        )
    builder.button(text="« Volver", callback_data=_tx(TxAction.BACK, transaction_id))
    builder.adjust(2)
    return builder.as_markup()


def account_picker(transaction_id: int, accounts: list[Account]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for account in accounts:
        builder.button(
            text=f"{account.emoji} {account.name}",
            callback_data=TxAccountCallback(tx_id=transaction_id, account_id=account.id),
        )
    builder.button(text="« Volver", callback_data=_tx(TxAction.BACK, transaction_id))
    builder.adjust(2)
    return builder.as_markup()


def delete_confirmation(transaction_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Sí, borrar", callback_data=_tx(TxAction.CONFIRM_DELETE, transaction_id))
    builder.button(text="« No", callback_data=_tx(TxAction.BACK, transaction_id))
    builder.adjust(2)
    return builder.as_markup()


def transactions_page(
    page: TransactionPage, month: tuple[int, int] | None
) -> InlineKeyboardMarkup | None:
    if not page.items:
        return None
    year, month_number = month or (0, 0)
    builder = InlineKeyboardBuilder()
    for transaction in page.items:
        builder.button(text=f"#{transaction.id}", callback_data=_tx(TxAction.OPEN, transaction.id))
    sizes = [5] * ((len(page.items) + 4) // 5)

    navigation = []
    if page.has_previous:
        navigation.append(("◀️ Anterior", page.number - 1))
    if page.has_next:
        navigation.append(("Siguiente ▶️", page.number + 1))
    for text, number in navigation:
        builder.button(
            text=text, callback_data=TxPageCallback(page=number, year=year, month=month_number)
        )
    if navigation:
        sizes.append(len(navigation))

    builder.adjust(*sizes)
    return builder.as_markup()


def _tx(action: TxAction, transaction_id: int) -> TxCallback:
    return TxCallback(action=action, tx_id=transaction_id)
