"""Small helpers shared by handlers."""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def edit_or_send(
    callback: CallbackQuery, bot: Bot, text: str, markup: InlineKeyboardMarkup | None
) -> None:
    """Edit the message holding the pressed button; send a new one if it is not accessible."""
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest as error:
            # Pressing a button that leads to the same content is not an error.
            if "message is not modified" not in error.message:
                raise
        return
    await bot.send_message(callback.from_user.id, text, reply_markup=markup)
