from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message

from asistente.bot.handlers.finance import keyboards, views
from asistente.config import Settings
from asistente.finance.service import FinanceService
from asistente.users.models import User


async def register_transaction(
    message: Message, finance: FinanceService, user: User, settings: Settings
) -> None:
    """Plain text outside any conversation step is a new transaction: ``uber 2000``."""
    transaction = await finance.register(user, message.text or "", now=message.date)
    await message.answer(
        views.transaction_card(transaction, settings.tz, title=views.registered_title(transaction)),
        reply_markup=keyboards.transaction_actions(transaction.id),
    )


def build_router() -> Router:
    router = Router(name="finance.entries")
    router.message.register(
        register_transaction, StateFilter(None), F.text, ~F.text.startswith("/")
    )
    return router
