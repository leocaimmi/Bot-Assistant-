"""Command menu shown by Telegram next to the message box."""

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats

BOT_COMMANDS = (
    BotCommand(command="resumen", description="Resumen del mes"),
    BotCommand(command="movimientos", description="Ver y editar movimientos"),
    BotCommand(command="categorias", description="Categorías y palabras clave"),
    BotCommand(command="ayuda", description="Cómo usar el bot"),
    BotCommand(command="cancelar", description="Cancelar la acción en curso"),
)


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(list(BOT_COMMANDS), scope=BotCommandScopeAllPrivateChats())
