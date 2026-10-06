from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.middlewares.base import Handler


class DbSessionMiddleware(BaseMiddleware):
    """Runs each handler inside one database transaction, exposed as ``session``.

    Commits when the handler succeeds and rolls back if it raises.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        async with self._session_factory() as session, session.begin():
            data["session"] = session
            return await handler(event, data)
