from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.bot.middlewares.base import Handler
from asistente.users.models import User
from asistente.users.service import UserService

# Prepares a module's data for a user (e.g. default categories). Must be idempotent:
# it runs when the user registers and again for every user at each startup.
UserSetupHook = Callable[[AsyncSession, User], Awaitable[None]]


class UserMiddleware(BaseMiddleware):
    """Loads the current user (registering it on first contact) and exposes it as ``user``.

    ``setup_hooks`` run right after a user is created, so each module can prepare its own
    initial data without the core knowing about it.
    """

    def __init__(self, setup_hooks: Sequence[UserSetupHook] = ()) -> None:
        self._setup_hooks = tuple(setup_hooks)

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        telegram_user: TelegramUser = data["event_from_user"]
        session: AsyncSession = data["session"]

        user, created = await UserService(session).get_or_create(telegram_user.id)
        if created:
            for hook in self._setup_hooks:
                await hook(session, user)

        data["user"] = user
        return await handler(event, data)
