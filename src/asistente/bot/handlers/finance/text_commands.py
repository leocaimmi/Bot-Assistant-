"""Text commands on transactions: "borrar uber 2000", "cambiar uber 2000 a 2500"."""

from zoneinfo import ZoneInfo

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from asistente.bot.handlers.finance import edits, keyboards, views
from asistente.finance.commands import CommandKind, TextCommand, split_new_value
from asistente.finance.service import FinanceService
from asistente.users.models import User


async def handle_command(
    message: Message,
    command: TextCommand,
    finance: FinanceService,
    user: User,
    tz: ZoneInfo,
    state: FSMContext,
) -> None:
    today = message.date.astimezone(tz).date()

    if command.kind is CommandKind.DELETE:
        transaction = await finance.find_by_text(user, command.rest, today=today)
        await message.answer(
            views.transaction_card(transaction, tz, title="¿Borrar este movimiento?"),
            reply_markup=keyboards.delete_confirmation(transaction.id),
        )
        return

    # "cambiar uber 2000 a 2500": show before → after and apply it on OK.
    if (parts := split_new_value(command.rest)) is not None:
        target_text, new_text = parts
        change = await finance.resolve_change(user, new_text, today=today)
        if change is not None:
            transaction = await finance.find_by_text(user, target_text, today=today)
            await edits.propose(message, transaction, [change], state, tz)
            return

    # "cambiar uber 2000": show every editable field.
    transaction = await finance.find_by_text(user, command.rest, today=today)
    await message.answer(
        views.transaction_card(transaction, tz, title="✏️ ¿Qué querés cambiar?"),
        reply_markup=keyboards.transaction_editor(transaction),
    )
