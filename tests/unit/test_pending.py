from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from asistente.bot import pending


def _state() -> FSMContext:
    return FSMContext(MemoryStorage(), StorageKey(bot_id=1, chat_id=2, user_id=2))


async def test_a_change_is_applied_once() -> None:
    state = _state()
    token = await pending.keep(state, "edit", {"id": 5})

    assert await pending.take(state, "edit", token) == {"id": 5, "token": token}
    assert await pending.take(state, "edit", token) is None


async def test_a_newer_change_replaces_the_older_one() -> None:
    state = _state()
    old = await pending.keep(state, "edit", {"id": 5})
    await pending.keep(state, "edit", {"id": 6})

    assert await pending.take(state, "edit", old) is None


async def test_keys_do_not_mix() -> None:
    state = _state()
    token = await pending.keep(state, "edit", {"id": 5})

    assert await pending.take(state, "other", token) is None
    assert await pending.take(state, "edit", token) is not None
