from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

from asistente.bot.middlewares.base import Handler


class CommandResetsStateMiddleware(BaseMiddleware):
    """Any command abandons a pending conversation step (e.g. "send me the new amount").

    Without this, a later "uber 2000" could be read as the answer to a forgotten question.
    Registered as an outer middleware so filters already see the cleared state. Handlers
    can ask for ``state_was_reset`` to know whether something was abandoned.
    """

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        state: FSMContext | None = data.get("state")
        is_command = isinstance(event, Message) and (event.text or "").startswith("/")
        if is_command and state is not None and data.get("raw_state") is not None:
            await state.clear()
            data["raw_state"] = None
            data["state_was_reset"] = True
        return await handler(event, data)
