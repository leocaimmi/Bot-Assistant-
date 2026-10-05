"""Gym commands and buttons. Workout messages are handled by ``free_text``."""

from datetime import date, datetime

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from asistente.bot.handlers.gym import keyboards, views
from asistente.bot.handlers.gym.callbacks import GymEntryCallback, GymUndoCallback
from asistente.bot.ui import edit_or_send
from asistente.config import Settings
from asistente.core.dates import parse_day
from asistente.gym.models import MuscleGroup
from asistente.gym.service import GymService, LoggedWorkout
from asistente.users.models import User


async def answer_logged(message: Message, logged: LoggedWorkout, today: date) -> None:
    """Reply to a just-logged workout, with a button to undo it."""
    await message.answer(views.logged_workout(logged, today), reply_markup=keyboards.undo(logged))


async def show_day(
    message: Message, command: CommandObject, gym: GymService, user: User, settings: Settings
) -> None:
    today = message.date.astimezone(settings.tz).date()
    day = parse_day(command.args, today) if command.args else today
    if day is None:
        await message.answer(views.INVALID_DAY)
        return
    workout = await gym.day(user, day)
    await message.answer(
        views.day_workout(workout, day, today), reply_markup=keyboards.day_entries(workout)
    )


async def show_week(message: Message, gym: GymService, user: User, settings: Settings) -> None:
    today = message.date.astimezone(settings.tz).date()
    await message.answer(views.week(await gym.week(user, today)))


async def show_history(
    message: Message, command: CommandObject, gym: GymService, user: User
) -> None:
    if not command.args:
        await message.answer(views.HISTORY_USAGE)
        return
    await message.answer(views.history(await gym.history(user, command.args)))


async def list_exercises(message: Message, gym: GymService, user: User) -> None:
    by_group: dict[MuscleGroup, list[str]] = {}
    for exercise in await gym.exercises(user):
        by_group.setdefault(exercise.muscle_group, []).append(exercise.name)
    order = list(MuscleGroup)
    groups = sorted(by_group.items(), key=lambda item: order.index(item[0]))
    await message.answer(views.exercises(groups))


async def undo_logged(
    callback: CallbackQuery, callback_data: GymUndoCallback, bot: Bot, gym: GymService, user: User
) -> None:
    count = await gym.delete_entries(user, callback_data.first_id, callback_data.last_id)
    await edit_or_send(callback, bot, views.undone(count), None)
    await callback.answer("Deshecho")


async def delete_entry(
    callback: CallbackQuery,
    callback_data: GymEntryCallback,
    bot: Bot,
    gym: GymService,
    user: User,
    settings: Settings,
) -> None:
    day = await gym.delete_entry(user, callback_data.entry_id)
    today = datetime.now(settings.tz).date()
    workout = await gym.day(user, day)
    await edit_or_send(
        callback, bot, views.day_workout(workout, day, today), keyboards.day_entries(workout)
    )
    await callback.answer("Borrado")


def build_router() -> Router:
    router = Router(name="gym")
    router.message.register(show_day, Command("entreno"))
    router.message.register(show_week, Command("semana"))
    router.message.register(show_history, Command("historial"))
    router.message.register(list_exercises, Command("ejercicios"))
    router.callback_query.register(undo_logged, GymUndoCallback.filter())
    router.callback_query.register(delete_entry, GymEntryCallback.filter())
    return router
