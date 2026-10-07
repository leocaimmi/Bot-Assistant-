"""/start, /ayuda (a menu of short help topics, browsed with buttons) and /cancelar."""

import html

from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from asistente.ai.interpreter import Interpreter
from asistente.bot.help import TOPIC_BUTTONS, HelpTopic, help_text
from asistente.bot.ui import edit_or_send

EXAMPLES_BUTTON = "💡 Ver ejemplos"


class HelpCallback(CallbackData, prefix="help"):
    topic: HelpTopic


async def start(
    message: Message, state: FSMContext, interpreter: Interpreter | None = None
) -> None:
    await state.clear()
    first_name = message.from_user.first_name if message.from_user else ""
    menu = help_text(HelpTopic.MENU, ai_enabled=interpreter is not None)
    greeting = f"¡Hola, {html.escape(first_name)}! 👋"
    await message.answer(f"{greeting}\n\n{menu}", reply_markup=help_keyboard(HelpTopic.MENU))


async def show_help(message: Message, interpreter: Interpreter | None = None) -> None:
    await message.answer(
        help_text(HelpTopic.MENU, ai_enabled=interpreter is not None),
        reply_markup=help_keyboard(HelpTopic.MENU),
    )


async def show_help_topic(
    callback: CallbackQuery,
    callback_data: HelpCallback,
    bot: Bot,
    interpreter: Interpreter | None = None,
) -> None:
    topic = callback_data.topic
    text = help_text(topic, ai_enabled=interpreter is not None)
    await edit_or_send(callback, bot, text, help_keyboard(topic))
    await callback.answer()


def help_keyboard(topic: HelpTopic) -> InlineKeyboardMarkup:
    """The menu shows a button per topic; each topic, a button back to the menu."""
    builder = InlineKeyboardBuilder()
    if topic is HelpTopic.MENU:
        for item, label in TOPIC_BUTTONS.items():
            builder.button(text=label, callback_data=HelpCallback(topic=item))
        builder.adjust(2)
    else:
        builder.button(text="« Menú", callback_data=HelpCallback(topic=HelpTopic.MENU))
    return builder.as_markup()


def examples_keyboard(topic: HelpTopic) -> InlineKeyboardMarkup:
    """A button that opens the examples of ``topic``: empty lists offer it instead of text."""
    builder = InlineKeyboardBuilder()
    builder.button(text=EXAMPLES_BUTTON, callback_data=HelpCallback(topic=topic))
    return builder.as_markup()


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
    router.callback_query.register(show_help_topic, HelpCallback.filter())
    return router
