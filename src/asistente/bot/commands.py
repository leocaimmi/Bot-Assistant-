"""Command menu shown by Telegram next to the message box."""

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats

BOT_COMMANDS = (
    BotCommand(command="ayuda", description="Cómo usar el bot"),
    BotCommand(command="cancelar", description="Cancelar la acción en curso"),
)


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(list(BOT_COMMANDS), scope=BotCommandScopeAllPrivateChats())
