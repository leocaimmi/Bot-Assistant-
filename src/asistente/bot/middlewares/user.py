from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.bot.middlewares.base import Handler
from asistente.users.models import User
from asistente.users.service import UserService

RegistrationHook = Callable[[AsyncSession, User], Awaitable[None]]


class UserMiddleware(BaseMiddleware):
    """Loads the current user (registering it on first contact) and exposes it as ``user``.

    ``registration_hooks`` run once, right after a user is created, so each module can
    prepare its own initial data without the core knowing about it.
    """

    def __init__(self, registration_hooks: Sequence[RegistrationHook] = ()) -> None:
        self._registration_hooks = tuple(registration_hooks)

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        telegram_user: TelegramUser = data["event_from_user"]
        session: AsyncSession = data["session"]

        user, created = await UserService(session).get_or_create(telegram_user.id)
        if created:
            for hook in self._registration_hooks:
                await hook(session, user)

        data["user"] = user
        return await handler(event, data)
