"""Command menu shown by Telegram next to the message box."""

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats

BOT_COMMANDS = (
    BotCommand(command="ayuda", description="Todo lo que podés hacer"),
    BotCommand(command="resumen", description="Resumen del mes"),
    BotCommand(command="movimientos", description="Ver y editar movimientos"),
    BotCommand(command="recordatorios", description="Tus recordatorios"),
    BotCommand(command="fijos", description="Cuotas y gastos fijos"),
    BotCommand(command="categorias", description="Categorías y palabras clave"),
    BotCommand(command="entreno", description="Entrenamiento de hoy (o de otro día)"),
    BotCommand(command="semana", description="Días entrenados esta semana"),
    BotCommand(command="historial", description="Progreso de un ejercicio"),
    BotCommand(command="ejercicios", description="Tus ejercicios por músculo"),
    BotCommand(command="ia", description="Uso y costo de la IA"),
    BotCommand(command="cancelar", description="Cancelar la acción en curso"),
)


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(list(BOT_COMMANDS), scope=BotCommandScopeAllPrivateChats())
