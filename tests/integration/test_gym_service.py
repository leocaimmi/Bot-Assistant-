from datetime import date, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.gym.models import Exercise, MuscleGroup, Workout
from asistente.gym.parser import ExerciseItem
from asistente.gym.service import (
    EntryNotFoundError,
    EntrySearch,
    ExerciseNotFoundError,
    GymService,
)
from asistente.users.models import User
from asistente.users.service import UserService
from tests.factories import STRANGER_USER_ID

MONDAY = date(2026, 10, 5)
CHEST = MuscleGroup.CHEST


def _item(
    name: str,
    sets: int = 4,
    reps: int = 12,
    kg: int | None = None,
    group: MuscleGroup | None = CHEST,
) -> ExerciseItem:
    return ExerciseItem(name, group, sets, reps, kg * 1000 if kg else None)


async def _count(session: AsyncSession, model: type[object]) -> int:
    return await session.scalar(select(func.count()).select_from(model)) or 0


async def test_log_creates_workout_and_reuses_exercises(
    session: AsyncSession, gym: GymService, user: User
) -> None:
    first = await gym.log(user, [_item("Banco plano", kg=60)], day=MONDAY)
    second = await gym.log(user, [_item("banco  PLANO", kg=65), _item("Fondos", 3, 10)], day=MONDAY)

    assert first.entries[0].exercise.id == second.entries[0].exercise.id
    assert await _count(session, Workout) == 1
    assert await _count(session, Exercise) == 2
    workout = await gym.day(user, MONDAY)
    assert workout is not None
    assert [(e.exercise.name, e.sets, e.reps, e.weight_grams) for e in workout.entries] == [
        ("Banco plano", 4, 12, 60_000),
        ("Banco plano", 4, 12, 65_000),
        ("Fondos", 3, 10, None),
    ]


async def test_exercise_learns_its_group_later(gym: GymService, user: User) -> None:
    await gym.log(user, [_item("Fondos", group=None)], day=MONDAY)
    logged = await gym.log(user, [_item("Fondos", group=MuscleGroup.TRICEPS)], day=MONDAY)

    assert logged.entries[0].exercise.muscle_group is MuscleGroup.TRICEPS


async def test_week_lists_days_and_groups(gym: GymService, user: User) -> None:
    await gym.log(
        user, [_item("Banco plano"), _item("Fondos", group=MuscleGroup.TRICEPS)], day=MONDAY
    )
    await gym.log(user, [_item("Sentadilla", group=MuscleGroup.LEGS)], day=date(2026, 10, 7))
    await gym.log(user, [_item("Remo", group=MuscleGroup.BACK)], day=date(2026, 10, 4))  # last week

    days = await gym.week(user, today=date(2026, 10, 8))

    assert [(d.day, d.groups, d.sets) for d in days] == [
        (MONDAY, (CHEST, MuscleGroup.TRICEPS), 8),
        (date(2026, 10, 7), (MuscleGroup.LEGS,), 4),
    ]


async def test_history_and_record(gym: GymService, user: User) -> None:
    await gym.log(user, [_item("Banco plano", 4, 12, kg=60)], day=date(2026, 9, 28))
    await gym.log(user, [_item("Banco plano", 4, 8, kg=70)], day=date(2026, 10, 1))
    await gym.log(user, [_item("Banco plano", 4, 10, kg=65)], day=MONDAY)

    result = await gym.history(user, "banco")

    assert result.exercise.name == "Banco plano"
    assert [(e.day, e.weight_grams) for e in result.entries] == [
        (MONDAY, 65_000),
        (date(2026, 10, 1), 70_000),
        (date(2026, 9, 28), 60_000),
    ]
    assert result.best is not None and result.best.weight_grams == 70_000


async def test_history_of_unknown_exercise(gym: GymService, user: User) -> None:
    with pytest.raises(ExerciseNotFoundError):
        await gym.history(user, "curl martillo")


async def test_undo_removes_entries_and_empty_workout(
    session: AsyncSession, gym: GymService, user: User
) -> None:
    logged = await gym.log(user, [_item("Banco plano"), _item("Fondos")], day=MONDAY)
    ids = [entry.id for entry in logged.entries]

    deleted = await gym.delete_entries(user, min(ids), max(ids))

    assert deleted == 2
    assert await _count(session, Workout) == 0


async def test_delete_one_entry_keeps_the_rest(gym: GymService, user: User) -> None:
    logged = await gym.log(user, [_item("Banco plano"), _item("Fondos")], day=MONDAY)

    day = await gym.delete_entry(user, logged.entries[0].id)

    workout = await gym.day(user, day)
    assert workout is not None
    assert [entry.exercise.name for entry in workout.entries] == ["Fondos"]


async def test_cannot_touch_other_users_entries(
    session: AsyncSession, gym: GymService, user: User
) -> None:
    stranger, _ = await UserService(session).get_or_create(STRANGER_USER_ID)
    foreign = await gym.log(stranger, [_item("Banco plano")], day=MONDAY)
    entry_id = foreign.entries[0].id

    with pytest.raises(EntryNotFoundError):
        await gym.delete_entry(user, entry_id)
    with pytest.raises(EntryNotFoundError):
        await gym.delete_entries(user, entry_id, entry_id)
    assert await gym.day(user, MONDAY) is None
    with pytest.raises(EntryNotFoundError):
        await gym.entry(user, entry_id)
    with pytest.raises(EntryNotFoundError):
        await gym.correct(user, entry_id, sets=3, reps=10, weight_grams=None)
    assert (await gym.find_entry(user, ("banco",), day=None)).day is None


async def test_correct_an_entry(gym: GymService, user: User) -> None:
    logged = await gym.log(user, [_item("Vuelos laterales", 3, 10)], day=MONDAY)

    entry = await gym.correct(user, logged.entries[0].id, sets=4, reps=8, weight_grams=7_500)

    assert (entry.sets, entry.reps, entry.weight_grams) == (4, 8, 7_500)
    assert (await gym.entry(user, entry.id)).workout.day == MONDAY


async def test_find_an_entry_by_name_and_day(gym: GymService, user: User) -> None:
    tuesday = MONDAY + timedelta(days=1)
    await gym.log(user, [_item("Press militar con barra"), _item("Vuelos laterales")], day=MONDAY)
    await gym.log(user, [_item("Press militar con barra")], day=tuesday)

    latest = await gym.find_entry(user, ("press", "militar"), day=None)
    on_monday = await gym.find_entry(user, ("lateral",), day=MONDAY)

    assert latest.entry is not None
    assert latest.entry.workout.day == tuesday
    assert on_monday.entry is not None
    assert on_monday.entry.exercise.name == "Vuelos laterales"


async def test_unclear_names_show_the_day(gym: GymService, user: User) -> None:
    tuesday = MONDAY + timedelta(days=1)
    await gym.log(user, [_item("Press militar"), _item("Press plano")], day=MONDAY)
    await gym.log(user, [_item("Sentadilla")], day=tuesday)

    assert await gym.find_entry(user, ("press",), day=None) == EntrySearch(None, MONDAY)
    assert await gym.find_entry(user, ("remo",), day=None) == EntrySearch(None, tuesday)
    assert await gym.find_entry(user, (), day=MONDAY) == EntrySearch(None, MONDAY)
    assert await gym.find_entry(user, (), day=MONDAY - timedelta(days=1)) == EntrySearch(
        None, MONDAY - timedelta(days=1)
    )


async def test_last_logged(gym: GymService, user: User) -> None:
    assert await gym.last_logged(user) is None
    await gym.log(user, [_item("Sentadilla")], day=MONDAY + timedelta(days=1))
    await gym.log(user, [_item("Banco plano")], day=MONDAY)

    last = await gym.last_logged(user)

    assert last is not None
    assert (last.exercise.name, last.workout.day) == ("Banco plano", MONDAY)
