import logging
from typing import Any

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Chat, TelegramObject, User

from asistente.bot.middlewares.base import Handler

logger = logging.getLogger(__name__)


class AccessMiddleware(BaseMiddleware):
    """Lets through only updates from allowed users in private chats.

    Everything else is dropped silently, so strangers cannot even tell the bot is alive.
    Registered as an outer middleware: it runs before any filter or handler.
    """

    def __init__(self, allowed_user_ids: frozenset[int]) -> None:
        self._allowed_user_ids = allowed_user_ids

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        user: User | None = data.get("event_from_user")
        chat: Chat | None = data.get("event_chat")

        if user is None or user.id not in self._allowed_user_ids:
            logger.warning("Ignored update from unauthorized user id=%s", user.id if user else None)
            return None
        if chat is not None and chat.type != ChatType.PRIVATE:
            logger.warning("Ignored update from a non-private chat (type=%s)", chat.type)
            return None
        return await handler(event, data)
