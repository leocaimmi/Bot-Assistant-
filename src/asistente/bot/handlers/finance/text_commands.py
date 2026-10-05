"""Text commands on transactions: "borrar uber 2000", "cambiar uber 2000 a 2500"."""

from html import escape
from zoneinfo import ZoneInfo

from aiogram.types import Message

from asistente.bot.handlers.finance import keyboards, views
from asistente.core.money import format_ars
from asistente.finance.commands import CommandKind, TextCommand, split_new_value
from asistente.finance.models import Transaction
from asistente.finance.service import (
    AmountChange,
    CategoryChange,
    Change,
    DayChange,
    FinanceService,
)
from asistente.users.models import User


async def handle_command(
    message: Message, command: TextCommand, finance: FinanceService, user: User, tz: ZoneInfo
) -> None:
    today = message.date.astimezone(tz).date()

    if command.kind is CommandKind.DELETE:
        transaction = await finance.find_by_text(user, command.rest, today=today)
        await message.answer(
            views.transaction_card(transaction, tz, title="¿Borrar este movimiento?"),
            reply_markup=keyboards.delete_confirmation(transaction.id),
        )
        return

    # "cambiar uber 2000 a 2500": apply right away (it can always be edited back).
    if (parts := split_new_value(command.rest)) is not None:
        target_text, new_text = parts
        change = await finance.resolve_change(user, new_text, today=today)
        if change is not None:
            transaction = await finance.find_by_text(user, target_text, today=today)
            label, before = _field(transaction, change, tz)
            updated = await finance.apply_change(user, transaction.id, change)
            _, after = _field(updated, change, tz)
            await message.answer(
                views.transaction_card(updated, tz, title=f"✏️ {label}: {before} → {after}"),
                reply_markup=keyboards.transaction_actions(updated.id),
            )
            return

    # "cambiar uber 2000": show every editable field.
    transaction = await finance.find_by_text(user, command.rest, today=today)
    await message.answer(
        views.transaction_card(transaction, tz, title="✏️ ¿Qué querés cambiar?"),
        reply_markup=keyboards.transaction_editor(transaction),
    )


def _field(transaction: Transaction, change: Change, tz: ZoneInfo) -> tuple[str, str]:
    """Label and current value (HTML-escaped) of the field that ``change`` touches."""
    match change:
        case AmountChange():
            return "Importe", format_ars(transaction.amount_cents)
        case CategoryChange():
            return "Categoría", escape(transaction.category.label)
        case DayChange():
            return "Fecha", f"{transaction.occurred_at.astimezone(tz):%d/%m/%Y}"
