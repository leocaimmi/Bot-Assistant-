import html

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from asistente.bot.help import HELP_TEXT


async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    first_name = message.from_user.first_name if message.from_user else ""
    await message.answer(f"¡Hola, {html.escape(first_name)}! 👋\n\n{HELP_TEXT}")


async def show_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


async def cancel(message: Message, state_was_reset: bool = False) -> None:
    # CommandResetsStateMiddleware already cleared any pending step before we got here.
    if state_was_reset:
        await message.answer("Listo, cancelado. ✋")
    else:
        await message.answer("No había nada para cancelar.")


def build_router() -> Router:
    router = Router(name="common")
    router.message.register(start, CommandStart())
    router.message.register(show_help, Command("ayuda", "help"))
    router.message.register(cancel, Command("cancelar", "cancel"))
    return router
