"""Text messages, typed or transcribed: a reminder, a command, a workout, a movement, or
(last) the AI.

Free rules first, in this order: "recordame..." is a reminder, even with an amount in it;
a leading verb is a command ("borrar uber 2000"); sets x
reps is a workout ("pecho: banco plano 4x12"); anything with an amount is a transaction
("uber 2000"). Only what the rules cannot handle goes to the AI, when it is configured.
"""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from asistente.ai.interpreter import Interpreter
from asistente.ai.usage import AiUsageService, DailyBudget
from asistente.bot.handlers import assistant
from asistente.bot.handlers import gym as gym_handlers
from asistente.bot.handlers import reminders as reminder_handlers
from asistente.bot.handlers.finance import entries as finance_entries
from asistente.bot.handlers.finance import text_commands
from asistente.bot.handlers.gym import views as gym_views
from asistente.bot.handlers.reminders import views as reminder_views
from asistente.config import Settings
from asistente.finance.commands import (
    TextCommand,
    is_simple_command,
    looks_like_correction,
    parse_command,
)
from asistente.finance.parser import MissingAmountError, is_simple_entry
from asistente.finance.service import (
    FinanceService,
    MissingTargetError,
    NoMatchingTransactionError,
)
from asistente.gym.parser import looks_like_workout, parse_workout
from asistente.gym.service import GymService
from asistente.reminders.parser import is_reminder_request, mentions_reminders
from asistente.reminders.service import ReminderService
from asistente.users.models import User

NOT_UNDERSTOOD = (
    "🤔 No te entendí. Algunos ejemplos:\n"
    "• Gasto: <code>uber 2000</code>\n"
    "• Ingreso: <code>transferencia utn 200.000</code>\n"
    f"• Entrenamiento: {gym_views.FORMAT_EXAMPLES}\n"
    "Mirá /ayuda para más."
)
CORRECTION_HELP = (
    "✏️ Para corregir un movimiento escribí, por ejemplo, "
    "<code>cambiar uber 2000 a 2500</code> o <code>borrar uber 2000</code>."
)


async def handle_free_text(
    message: Message,
    finance: FinanceService,
    gym: GymService,
    ai_usage: AiUsageService,
    reminders: ReminderService,
    user: User,
    settings: Settings,
    state: FSMContext,
    ai_budget: DailyBudget,
    interpreter: Interpreter | None = None,
) -> None:
    await route_text(
        message,
        message.text or "",
        finance=finance,
        gym=gym,
        reminders=reminders,
        ai_usage=ai_usage,
        user=user,
        settings=settings,
        state=state,
        ai_budget=ai_budget,
        interpreter=interpreter,
    )


async def route_text(
    message: Message,
    text: str,
    *,
    finance: FinanceService,
    gym: GymService,
    reminders: ReminderService,
    ai_usage: AiUsageService,
    user: User,
    settings: Settings,
    state: FSMContext,
    ai_budget: DailyBudget,
    interpreter: Interpreter | None,
) -> None:
    """Act on ``text`` and answer ``message`` (whose text may be a transcript)."""
    ai_on = interpreter is not None
    command = parse_command(text)
    if command is not None and mentions_reminders(text):
        # "borrar el recordatorio de la pastilla": reminders have their own list.
        await message.answer(reminder_views.USE_THE_LIST)
        return
    # Reminders: "recordame pagar 2000 de luz" is not an expense.
    if is_reminder_request(text):
        if await reminder_handlers.create_from_text(message, text, reminders, user, settings):
            return
        if not ai_on:
            await message.answer(reminder_views.NOT_UNDERSTOOD)
            return
        # The rules could not read the timing: the AI does (below).
    # Commands: "borrar uber 2000" must not register a new expense.
    elif command is not None:
        if await _run_command(message, command, text, finance, user, settings, state, ai_on=ai_on):
            return
    elif await _run_rules(message, text, finance, gym, user, settings, ai_on=ai_on):
        return

    if interpreter is not None and await assistant.interpret(
        message,
        text,
        interpreter=interpreter,
        budget=ai_budget,
        finance=finance,
        gym=gym,
        ai_usage=ai_usage,
        user=user,
        settings=settings,
        state=state,
    ):
        return
    await message.answer(_help_for(text))


async def _run_command(
    message: Message,
    command: TextCommand,
    text: str,
    finance: FinanceService,
    user: User,
    settings: Settings,
    state: FSMContext,
    *,
    ai_on: bool,
) -> bool:
    """Short commands with the rules; ``False`` lets the AI read long or unresolved ones."""
    if ai_on and not is_simple_command(text):
        return False
    try:
        await text_commands.handle_command(message, command, finance, user, settings.tz, state)
    except (MissingTargetError, NoMatchingTransactionError):
        if not ai_on:
            raise
        return False
    return True


async def _run_rules(
    message: Message,
    text: str,
    finance: FinanceService,
    gym: GymService,
    user: User,
    settings: Settings,
    *,
    ai_on: bool,
) -> bool:
    """A workout or a simple movement with the free rules; ``False`` if neither applies."""
    today = message.date.astimezone(settings.tz).date()
    # Workouts: "banco plano 4x12 60" must not become a $60 expense.
    if (workout := parse_workout(text, today)) is not None:
        logged = await gym.log(user, workout.items, day=workout.day or today)
        await gym_handlers.answer_logged(message, logged, today)
        return True

    # A plain amount is a transaction, unless it reads like a workout or a correction
    # ("el uber eran 2500"): those are never registered as something new. With the AI on,
    # only simple entries take this path; longer ones are better understood by the AI.
    if looks_like_workout(text) or looks_like_correction(text):
        return False
    if ai_on and not is_simple_entry(text):
        return False
    try:
        transaction = await finance.register(user, text, now=message.date)
    except MissingAmountError:
        return False
    await finance_entries.answer_registered(message, transaction, settings.tz)
    return True


def _help_for(text: str) -> str:
    if looks_like_workout(text):
        return gym_views.WORKOUT_FORMAT_HELP
    if looks_like_correction(text):
        return CORRECTION_HELP
    return NOT_UNDERSTOOD


def build_router() -> Router:
    router = Router(name="free_text")
    router.message.register(handle_free_text, StateFilter(None), F.text, ~F.text.startswith("/"))
    return router
