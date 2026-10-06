from typing import Any

from aiogram import BaseMiddleware, Router
from aiogram.types import TelegramObject

from asistente.bot.handlers.finance import categories, entries, reports, transactions
from asistente.bot.middlewares.base import Handler
from asistente.config import Settings
from asistente.finance.categories import CategoryService
from asistente.finance.service import FinanceService


class FinanceServiceMiddleware(BaseMiddleware):
    """Gives finance handlers ready services (``finance``, ``category_service``) bound to
    the update's database session."""

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        settings: Settings = data["settings"]
        data["finance"] = FinanceService(data["session"], settings.tz)
        data["category_service"] = CategoryService(data["session"])
        return await handler(event, data)


def build_router() -> Router:
    router = Router(name="finance")
    router.message.middleware(FinanceServiceMiddleware())
    router.callback_query.middleware(FinanceServiceMiddleware())
    # Commands and buttons first; free text ("uber 2000") is the catch-all of the module.
    router.include_routers(
        transactions.build_router(),
        reports.build_router(),
        categories.build_router(),
        entries.build_router(),
    )
    return router
