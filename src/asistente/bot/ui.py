"""Small helpers shared by handlers."""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

TELEGRAM_MESSAGE_LIMIT = 4096


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split a long text on line breaks so each part fits in one Telegram message.

    Only a single line longer than ``limit`` is cut in the middle.
    """
    parts: list[str] = []
    lines: list[str] = []
    size = 0
    for line in text.split("\n"):
        pieces = [line[start : start + limit] for start in range(0, len(line), limit)] or [""]
        for piece in pieces:
            extra = len(piece) + (1 if lines else 0)  # +1 for the joining line break
            if lines and size + extra > limit:
                parts.append("\n".join(lines))
                lines, size, extra = [], 0, len(piece)
            lines.append(piece)
            size += extra
    if lines:
        parts.append("\n".join(lines))
    return parts


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
