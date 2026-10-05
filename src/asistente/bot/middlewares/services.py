from collections.abc import Callable, Mapping
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.bot.middlewares.base import Handler
from asistente.config import Settings

# Builds the services of every module for one update, e.g. {"finance": FinanceService(...)}.
ServicesFactory = Callable[[AsyncSession, Settings], Mapping[str, object]]


class ServicesMiddleware(BaseMiddleware):
    """Exposes the module services, bound to the update's database session, to handlers.

    The factory lives in the composition root (``bot.app``), so this middleware does not
    depend on any module.
    """

    def __init__(self, factory: ServicesFactory) -> None:
        self._factory = factory

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        data.update(self._factory(data["session"], data["settings"]))
        return await handler(event, data)
