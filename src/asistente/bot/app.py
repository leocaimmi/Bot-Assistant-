"""Wires the bot together and runs it with long polling."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.commands import set_bot_commands
from asistente.bot.errors import on_error
from asistente.bot.handlers import common, fallback
from asistente.bot.middlewares import (
    AccessMiddleware,
    CommandResetsStateMiddleware,
    DbSessionMiddleware,
    RegistrationHook,
    UserMiddleware,
)
from asistente.config import Settings
from asistente.db.engine import create_engine, create_session_factory

logger = logging.getLogger(__name__)

# Initial data each module needs for a brand-new user.
REGISTRATION_HOOKS: tuple[RegistrationHook, ...] = ()


def build_dispatcher(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> Dispatcher:
    # Keyword arguments become "workflow data", injectable into any handler.
    dispatcher = Dispatcher(storage=MemoryStorage(), settings=settings)

    # Access control first: nothing else runs for unauthorized updates.
    dispatcher.update.outer_middleware(AccessMiddleware(settings.allowed_user_ids))
    dispatcher.message.outer_middleware(CommandResetsStateMiddleware())
    for observer in (dispatcher.message, dispatcher.callback_query):
        observer.middleware(DbSessionMiddleware(session_factory))
        observer.middleware(UserMiddleware(REGISTRATION_HOOKS))

    dispatcher.include_routers(
        common.build_router(),
        fallback.build_router(),  # must stay last
    )
    dispatcher.errors.register(on_error)
    return dispatcher


def build_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )


async def run_polling(settings: Settings) -> None:
    """Long polling: the bot pulls updates, so no HTTP port is exposed to the internet."""
    engine = create_engine(settings.database_url.get_secret_value())
    dispatcher = build_dispatcher(settings, create_session_factory(engine))
    bot = build_bot(settings)
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await set_bot_commands(bot)
        logger.info("Bot started (long polling)")
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await engine.dispose()
        logger.info("Bot stopped")
