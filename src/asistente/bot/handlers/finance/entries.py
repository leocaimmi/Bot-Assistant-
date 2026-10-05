from zoneinfo import ZoneInfo

from aiogram.types import Message

from asistente.bot.handlers.finance import keyboards, views
from asistente.finance.models import Transaction


async def answer_registered(message: Message, transaction: Transaction, tz: ZoneInfo) -> None:
    """Reply with the card of a just-registered transaction and its action buttons."""
    await message.answer(
        views.transaction_card(transaction, tz, title=views.registered_title(transaction)),
        reply_markup=keyboards.transaction_actions(transaction.id),
    )
