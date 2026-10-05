"""Wires the bot together and runs it with long polling."""

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.ai.interpreter import Interpreter, OpenAIInterpreter, create_interpreter
from asistente.ai.usage import AiUsageService, DailyBudget
from asistente.bot.commands import set_bot_commands
from asistente.bot.errors import on_error
from asistente.bot.handlers import assistant, common, fallback, finance, free_text, gym
from asistente.bot.middlewares import (
    AccessMiddleware,
    CommandResetsStateMiddleware,
    DbSessionMiddleware,
    ServicesMiddleware,
    UserMiddleware,
    UserSetupHook,
)
from asistente.config import Settings
from asistente.db.engine import create_engine, create_session_factory
from asistente.finance.categories import CategoryService
from asistente.finance.defaults import seed_defaults
from asistente.finance.service import FinanceService
from asistente.gym.service import GymService
from asistente.users.service import UserService

logger = logging.getLogger(__name__)

# Data each module prepares for a user (see UserSetupHook).
USER_SETUP_HOOKS: tuple[UserSetupHook, ...] = (seed_defaults,)


def build_services(session: AsyncSession, settings: Settings) -> dict[str, object]:
    """Services available to handlers by name, bound to the update's session."""
    return {
        "finance": FinanceService(session, settings.tz),
        "category_service": CategoryService(session),
        "gym": GymService(session),
        "ai_usage": AiUsageService(session),
    }


def build_dispatcher(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    interpreter: Interpreter | None = None,
) -> Dispatcher:
    # Keyword arguments become "workflow data", injectable into any handler.
    dispatcher = Dispatcher(
        storage=MemoryStorage(),
        settings=settings,
        interpreter=interpreter,  # None: rules only
        ai_budget=DailyBudget(settings.ai_daily_limit),
    )

    # Access control first: nothing else runs for unauthorized updates.
    dispatcher.update.outer_middleware(AccessMiddleware(settings.allowed_user_ids))
    dispatcher.message.outer_middleware(CommandResetsStateMiddleware())
    for observer in (dispatcher.message, dispatcher.callback_query):
        observer.middleware(DbSessionMiddleware(session_factory))
        observer.middleware(UserMiddleware(USER_SETUP_HOOKS))
        observer.middleware(ServicesMiddleware(build_services))

    dispatcher.include_routers(
        common.build_router(),
        finance.build_router(),
        gym.build_router(),
        assistant.build_router(),
        free_text.build_router(),  # plain text: commands, workouts, transactions, AI
        fallback.build_router(),  # must stay last
    )
    dispatcher.errors.register(on_error)
    return dispatcher


def build_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )


async def set_up_existing_users(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Run the setup hooks for every user, so new defaults reach existing users too."""
    async with session_factory() as session, session.begin():
        for user in await UserService(session).all():
            for hook in USER_SETUP_HOOKS:
                await hook(session, user)


async def run_polling(settings: Settings) -> None:
    """Long polling: the bot pulls updates, so no HTTP port is exposed to the internet."""
    engine = create_engine(settings.database_url.get_secret_value())
    session_factory = create_session_factory(engine)
    interpreter = _build_interpreter(settings)
    dispatcher = build_dispatcher(settings, session_factory, interpreter)
    bot = build_bot(settings)
    try:
        await set_up_existing_users(session_factory)
        await bot.delete_webhook(drop_pending_updates=False)
        await set_bot_commands(bot)
        logger.info("Bot started (long polling, AI %s)", "on" if interpreter else "off")
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        if interpreter is not None:
            await interpreter.close()
        await engine.dispose()
        logger.info("Bot stopped")


def _build_interpreter(settings: Settings) -> OpenAIInterpreter | None:
    if not settings.ai_enabled or settings.openai_api_key is None:
        return None
    return create_interpreter(settings.openai_api_key.get_secret_value(), settings.openai_model)
