"""Fixing something without saying what ("quiero editar algo"): the latest thing logged.

A movement or a workout, whichever was registered last. The rules answer it, so these
messages never reach the AI.
"""

from aiogram.types import Message

from asistente.bot.handlers import gym as gym_handlers
from asistente.bot.handlers.finance import edits as finance_edits
from asistente.config import Settings
from asistente.finance.service import FinanceService
from asistente.gym.service import GymService
from asistente.users.models import User

NOTHING_TO_EDIT = "📭 Todavía no anotaste nada para corregir."


async def edit_latest(
    message: Message, finance: FinanceService, gym: GymService, user: User, settings: Settings
) -> None:
    """The editor of the latest movement, or the latest workout with a button per exercise."""
    transaction = await finance.last_registered(user)
    entry = await gym.last_logged(user)
    if entry is not None and (transaction is None or entry.created_at > transaction.created_at):
        today = message.date.astimezone(settings.tz).date()
        await gym_handlers.answer_day(message, gym, user, entry.workout.day, today)
    elif transaction is not None:
        await finance_edits.show_editor(message, transaction, settings.tz)
    else:
        await message.answer(NOTHING_TO_EDIT)
