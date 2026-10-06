from datetime import UTC, datetime
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, TelegramObject

from asistente.bot.middlewares import CommandResetsStateMiddleware

PENDING = "EditTransaction:amount"


async def _handler(_event: TelegramObject, _data: dict[str, Any]) -> None:
    return None


def _message(text: str) -> Message:
    return Message(message_id=1, date=datetime.now(UTC), chat=Chat(id=1, type="private"), text=text)


async def _pending_state() -> FSMContext:
    state = FSMContext(MemoryStorage(), StorageKey(bot_id=1, chat_id=1, user_id=1))
    await state.set_state(PENDING)
    return state


async def test_command_clears_pending_state() -> None:
    state = await _pending_state()
    data: dict[str, Any] = {"state": state, "raw_state": PENDING}

    await CommandResetsStateMiddleware()(_handler, _message("/movimientos"), data)

    assert await state.get_state() is None
    assert data["raw_state"] is None
    assert data["state_was_reset"] is True


async def test_plain_text_keeps_pending_state() -> None:
    state = await _pending_state()
    data: dict[str, Any] = {"state": state, "raw_state": PENDING}

    await CommandResetsStateMiddleware()(_handler, _message("2500"), data)

    assert await state.get_state() == PENDING
    assert "state_was_reset" not in data
