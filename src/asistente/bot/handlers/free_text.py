"""Plain-text messages: figure out whether they are a workout or a money movement.

Rules only, no external calls: a message with sets x reps is a workout ("pecho: banco
plano 4x12"); anything with an amount is a transaction ("uber 2000").
"""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message

from asistente.bot.handlers import gym as gym_handlers
from asistente.bot.handlers.finance import entries as finance_entries
from asistente.bot.handlers.gym import views as gym_views
from asistente.config import Settings
from asistente.finance.parser import MissingAmountError
from asistente.finance.service import FinanceService
from asistente.gym.parser import looks_like_workout, parse_workout
from asistente.gym.service import GymService
from asistente.users.models import User

NOT_UNDERSTOOD = (
    "🤔 No te entendí. Algunos ejemplos:\n"
    "• Gasto: <code>uber 2000</code>\n"
    "• Ingreso: <code>transferencia utn 200.000</code>\n"
    f"• Entrenamiento: {gym_views.FORMAT_EXAMPLES}\n"
    "Mirá /ayuda para más."
)


async def handle_free_text(
    message: Message, finance: FinanceService, gym: GymService, user: User, settings: Settings
) -> None:
    text = message.text or ""
    today = message.date.astimezone(settings.tz).date()

    # Workouts first: "banco plano 4x12 60" must not become a $60 expense.
    if (workout := parse_workout(text, today)) is not None:
        logged = await gym.log(user, workout.items, day=workout.day or today)
        await gym_handlers.answer_logged(message, logged, today)
        return
    if looks_like_workout(text):
        await message.answer(gym_views.WORKOUT_FORMAT_HELP)
        return

    try:
        transaction = await finance.register(user, text, now=message.date)
    except MissingAmountError:
        await message.answer(NOT_UNDERSTOOD)
        return
    await finance_entries.answer_registered(message, transaction, settings.tz)


def build_router() -> Router:
    router = Router(name="free_text")
    router.message.register(handle_free_text, StateFilter(None), F.text, ~F.text.startswith("/"))
    return router
