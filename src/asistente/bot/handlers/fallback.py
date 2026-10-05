"""Last-resort handlers. This router must be included after every other one."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message


async def unknown_command(message: Message) -> None:
    await message.answer("🤔 No conozco ese comando. Mirá /ayuda.")


async def unknown_text(message: Message) -> None:
    await message.answer("🤔 No entendí ese mensaje. Mirá /ayuda.")


async def unsupported_message(message: Message) -> None:
    await message.answer("Por ahora solo entiendo mensajes de texto. Mirá /ayuda.")


async def stale_button(callback: CallbackQuery) -> None:
    await callback.answer("Este botón ya no está disponible.")


def build_router() -> Router:
    router = Router(name="fallback")
    router.message.register(unknown_command, F.text.startswith("/"))
    router.message.register(unknown_text, F.text)
    router.message.register(unsupported_message)
    router.callback_query.register(stale_button)
    return router
