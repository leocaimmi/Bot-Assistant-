"""Gym commands and buttons. Workout messages are handled by ``free_text``.

Fixes written or dictated ("cambiar press militar a 40kg") are shown as before → after
and applied on OK, like the edits of movements.
"""

from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from asistente.bot import pending
from asistente.bot.handlers.gym import keyboards, views
from asistente.bot.handlers.gym.callbacks import (
    GymDayCallback,
    GymEditConfirmCallback,
    GymEntryAction,
    GymEntryCallback,
    GymUndoCallback,
)
from asistente.bot.handlers.gym.states import EditWorkoutEntry
from asistente.bot.ui import edit_or_send
from asistente.config import Settings
from asistente.core.dates import parse_day
from asistente.gym.edits import WorkoutEdit
from asistente.gym.models import MuscleGroup, WorkoutEntry
from asistente.gym.parser import SetChange, parse_set_change
from asistente.gym.service import GymService, LoggedWorkout
from asistente.users.models import User

PENDING_EDIT_KEY = "pending_gym_edit"


async def answer_logged(message: Message, logged: LoggedWorkout, today: date) -> None:
    """Reply to a just-logged workout, with buttons to undo or correct it."""
    await message.answer(
        views.logged_workout(logged, today), reply_markup=keyboards.logged_actions(logged)
    )


async def show_day(
    message: Message, command: CommandObject, gym: GymService, user: User, settings: Settings
) -> None:
    today = message.date.astimezone(settings.tz).date()
    day = parse_day(command.args, today) if command.args else today
    if day is None:
        await message.answer(views.INVALID_DAY)
        return
    await answer_day(message, gym, user, day, today)


async def answer_day(message: Message, gym: GymService, user: User, day: date, today: date) -> None:
    """The workout of ``day``, with a button per exercise to correct or delete it."""
    workout = await gym.day(user, day)
    await message.answer(
        views.day_workout(workout, day, today), reply_markup=keyboards.day_entries(workout)
    )


async def edit_from_text(
    message: Message,
    edit: WorkoutEdit,
    gym: GymService,
    user: User,
    settings: Settings,
    state: FSMContext,
) -> None:
    """A fix typed or dictated: the change to confirm, else the exercise or its day."""
    today = message.date.astimezone(settings.tz).date()
    found = await gym.find_entry(user, edit.exercise, day=edit.day)
    if found.entry is None:
        if found.day is None:
            await message.answer(views.NOTHING_LOGGED)
        else:
            await answer_day(message, gym, user, found.day, today)
        return
    if edit.change is None:
        await message.answer(
            views.entry_card(found.entry, today), reply_markup=keyboards.entry_actions(found.entry)
        )
        return
    await _propose(message, found.entry, edit.change, state, today)


async def _propose(
    message: Message, entry: WorkoutEntry, change: SetChange, state: FSMContext, today: date
) -> None:
    current = (entry.sets, entry.reps, entry.weight_grams)
    sets, reps, weight_grams = change.applied_to(*current)
    if (sets, reps, weight_grams) == current:
        await message.answer(
            views.entry_card(entry, today, title=views.ALREADY_LIKE_THAT),
            reply_markup=keyboards.entry_actions(entry),
        )
        return
    fix = {"entry_id": entry.id, "sets": sets, "reps": reps, "weight_grams": weight_grams}
    token = await pending.keep(state, PENDING_EDIT_KEY, fix)
    title = views.change_preview(entry, sets, reps, weight_grams)
    await message.answer(
        views.entry_card(entry, today, title=title), reply_markup=keyboards.confirm_edit(token)
    )


async def resolve_edit(
    callback: CallbackQuery,
    callback_data: GymEditConfirmCallback,
    state: FSMContext,
    bot: Bot,
    gym: GymService,
    user: User,
    settings: Settings,
) -> None:
    fix = await pending.take(state, PENDING_EDIT_KEY, callback_data.token)
    if fix is None:
        await callback.answer(views.CHANGE_UNAVAILABLE, show_alert=True)
        return
    if not callback_data.apply:
        await edit_or_send(callback, bot, views.CHANGE_DISCARDED, None)
        await callback.answer()
        return
    weight = fix["weight_grams"]
    entry = await gym.correct(
        user,
        int(fix["entry_id"]),
        sets=int(fix["sets"]),
        reps=int(fix["reps"]),
        weight_grams=int(weight) if weight is not None else None,
    )
    today = datetime.now(settings.tz).date()
    await edit_or_send(
        callback,
        bot,
        views.entry_card(entry, today, title=views.UPDATED),
        keyboards.entry_actions(entry),
    )
    await callback.answer("Cambios aplicados")


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


async def open_day(
    callback: CallbackQuery,
    callback_data: GymDayCallback,
    bot: Bot,
    gym: GymService,
    user: User,
    settings: Settings,
) -> None:
    await _show_day(callback, bot, gym, user, callback_data.day, settings)
    await callback.answer()


async def open_entry(
    callback: CallbackQuery,
    callback_data: GymEntryCallback,
    bot: Bot,
    gym: GymService,
    user: User,
    settings: Settings,
) -> None:
    entry = await gym.entry(user, callback_data.entry_id)
    today = datetime.now(settings.tz).date()
    await edit_or_send(
        callback, bot, views.entry_card(entry, today), keyboards.entry_actions(entry)
    )
    await callback.answer()


async def ask_values(
    callback: CallbackQuery,
    callback_data: GymEntryCallback,
    state: FSMContext,
    bot: Bot,
    gym: GymService,
    user: User,
) -> None:
    await gym.entry(user, callback_data.entry_id)  # fail early if it no longer exists
    await state.set_state(EditWorkoutEntry.values)
    await state.update_data(entry_id=callback_data.entry_id)
    await bot.send_message(callback.from_user.id, views.ASK_VALUES)
    await callback.answer()


async def receive_values(
    message: Message, state: FSMContext, gym: GymService, user: User, settings: Settings
) -> None:
    change = parse_set_change(message.text or "")
    if change is None:
        await message.answer(views.INVALID_VALUES)
        return
    entry_id = int((await state.get_data())["entry_id"])
    await state.clear()  # the step ends here even if the update fails
    entry = await gym.entry(user, entry_id)
    sets, reps, weight_grams = change.applied_to(entry.sets, entry.reps, entry.weight_grams)
    entry = await gym.correct(user, entry_id, sets=sets, reps=reps, weight_grams=weight_grams)
    today = message.date.astimezone(settings.tz).date()
    await message.answer(
        views.entry_card(entry, today, title=views.UPDATED),
        reply_markup=keyboards.entry_actions(entry),
    )


async def delete_entry(
    callback: CallbackQuery,
    callback_data: GymEntryCallback,
    bot: Bot,
    gym: GymService,
    user: User,
    settings: Settings,
) -> None:
    day = await gym.delete_entry(user, callback_data.entry_id)
    await _show_day(callback, bot, gym, user, day, settings)
    await callback.answer("Borrado")


async def _show_day(
    callback: CallbackQuery, bot: Bot, gym: GymService, user: User, day: date, settings: Settings
) -> None:
    today = datetime.now(settings.tz).date()
    workout = await gym.day(user, day)
    await edit_or_send(
        callback, bot, views.day_workout(workout, day, today), keyboards.day_entries(workout)
    )


def build_router() -> Router:
    router = Router(name="gym")
    router.message.register(show_day, Command("entreno"))
    router.message.register(show_week, Command("semana"))
    router.message.register(show_history, Command("historial"))
    router.message.register(list_exercises, Command("ejercicios"))
    router.callback_query.register(undo_logged, GymUndoCallback.filter())
    router.callback_query.register(open_day, GymDayCallback.filter())
    router.callback_query.register(resolve_edit, GymEditConfirmCallback.filter())
    entry_actions: dict[GymEntryAction, Callable[..., Awaitable[Any]]] = {
        GymEntryAction.OPEN: open_entry,
        GymEntryAction.EDIT: ask_values,
        GymEntryAction.DELETE: delete_entry,
    }
    for action, handler in entry_actions.items():
        router.callback_query.register(handler, GymEntryCallback.filter(F.action == action))
    router.message.register(
        receive_values, StateFilter(EditWorkoutEntry.values), F.text, ~F.text.startswith("/")
    )
    return router
