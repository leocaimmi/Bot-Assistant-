from datetime import UTC, datetime
from typing import Any

from aiogram.types import Chat, Message, TelegramObject, User

from asistente.bot.middlewares import AccessMiddleware
from tests.factories import ALLOWED_USER_ID, STRANGER_USER_ID

EVENT = Message(message_id=1, date=datetime.now(UTC), chat=Chat(id=1, type="private"))


async def _handler(_event: TelegramObject, _data: dict[str, Any]) -> str:
    return "handled"


def _data(user_id: int | None, chat_type: str = "private") -> dict[str, Any]:
    user = User(id=user_id, is_bot=False, first_name="x") if user_id is not None else None
    return {"event_from_user": user, "event_chat": Chat(id=1, type=chat_type)}


async def test_allows_whitelisted_user_in_private_chat() -> None:
    middleware = AccessMiddleware(frozenset({ALLOWED_USER_ID}))

    assert await middleware(_handler, EVENT, _data(ALLOWED_USER_ID)) == "handled"


async def test_blocks_unknown_user() -> None:
    middleware = AccessMiddleware(frozenset({ALLOWED_USER_ID}))

    assert await middleware(_handler, EVENT, _data(STRANGER_USER_ID)) is None


async def test_blocks_updates_without_user() -> None:
    middleware = AccessMiddleware(frozenset({ALLOWED_USER_ID}))

    assert await middleware(_handler, EVENT, _data(None)) is None


async def test_blocks_allowed_user_in_groups() -> None:
    middleware = AccessMiddleware(frozenset({ALLOWED_USER_ID}))

    assert await middleware(_handler, EVENT, _data(ALLOWED_USER_ID, "supergroup")) is None
