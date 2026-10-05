"""Business rules of the gym module. Every operation is scoped to the given user."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from asistente.core.errors import UserError
from asistente.core.text import normalize
from asistente.gym.models import Exercise, MuscleGroup, Workout, WorkoutEntry
from asistente.gym.parser import ExerciseItem
from asistente.users.models import User

HISTORY_SIZE = 10


class ExerciseNotFoundError(UserError):
    def __init__(self) -> None:
        super().__init__("🤔 No encontré ese ejercicio. Mirá tus ejercicios con /ejercicios.")


class EntryNotFoundError(UserError):
    def __init__(self) -> None:
        super().__init__("Ese registro ya no existe.")


@dataclass(frozen=True, slots=True)
class LoggedWorkout:
    day: date
    entries: list[WorkoutEntry]  # with ``exercise`` loaded


@dataclass(frozen=True, slots=True)
class DaySummary:
    day: date
    groups: tuple[MuscleGroup, ...]
    sets: int


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    day: date
    sets: int
    reps: int
    weight_grams: int | None


@dataclass(frozen=True, slots=True)
class ExerciseHistory:
    exercise: Exercise
    entries: list[HistoryEntry]  # newest first
    best: HistoryEntry | None  # heaviest weight (or most reps when there is no weight)


class GymService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(self, user: User, items: Sequence[ExerciseItem], *, day: date) -> LoggedWorkout:
        """Add exercises to the workout of ``day`` (created on the first log of the day)."""
        workout = await self._session.scalar(
            select(Workout).where(Workout.user_id == user.id, Workout.day == day)
        )
        if workout is None:
            workout = Workout(user_id=user.id, day=day, entries=[])
            self._session.add(workout)
            await self._session.flush()

        entries = []
        for item in items:
            entry = WorkoutEntry(
                workout_id=workout.id,
                exercise=await self._exercise(user, item.name, item.muscle_group),
                sets=item.sets,
                reps=item.reps,
                weight_grams=item.weight_grams,
            )
            self._session.add(entry)
            entries.append(entry)
        await self._session.flush()
        return LoggedWorkout(day=day, entries=entries)

    async def day(self, user: User, day: date) -> Workout | None:
        query = (
            select(Workout)
            .options(selectinload(Workout.entries).joinedload(WorkoutEntry.exercise))
            .where(Workout.user_id == user.id, Workout.day == day)
        )
        return await self._session.scalar(query)

    async def week(self, user: User, today: date) -> list[DaySummary]:
        """Days trained from Monday of this week until today."""
        monday = today - timedelta(days=today.weekday())
        query = (
            select(Workout)
            .options(selectinload(Workout.entries).joinedload(WorkoutEntry.exercise))
            .where(Workout.user_id == user.id, Workout.day >= monday, Workout.day <= today)
            .order_by(Workout.day)
        )
        summaries = []
        for workout in await self._session.scalars(query):
            groups = dict.fromkeys(entry.exercise.muscle_group for entry in workout.entries)
            sets = sum(entry.sets for entry in workout.entries)
            summaries.append(DaySummary(day=workout.day, groups=tuple(groups), sets=sets))
        return summaries

    async def history(self, user: User, query_text: str) -> ExerciseHistory:
        exercise = await self._find_exercise(user, query_text)
        rows = await self._session.execute(
            select(Workout.day, WorkoutEntry.sets, WorkoutEntry.reps, WorkoutEntry.weight_grams)
            .join(Workout, WorkoutEntry.workout_id == Workout.id)
            .where(Workout.user_id == user.id, WorkoutEntry.exercise_id == exercise.id)
            .order_by(Workout.day.desc(), WorkoutEntry.id.desc())
        )
        entries = [HistoryEntry(*row) for row in rows]
        best = max(entries, key=lambda e: (e.weight_grams or 0, e.reps), default=None)
        return ExerciseHistory(exercise=exercise, entries=entries[:HISTORY_SIZE], best=best)

    async def exercises(self, user: User) -> list[Exercise]:
        query = select(Exercise).where(Exercise.user_id == user.id).order_by(Exercise.key)
        return list(await self._session.scalars(query))

    async def delete_entries(self, user: User, first_id: int, last_id: int) -> int:
        """Delete the user's entries with ids in ``[first_id, last_id]`` (one logged message)."""
        entries = list(
            await self._session.scalars(
                select(WorkoutEntry)
                .join(Workout, WorkoutEntry.workout_id == Workout.id)
                .where(
                    Workout.user_id == user.id,
                    WorkoutEntry.id >= first_id,
                    WorkoutEntry.id <= last_id,
                )
            )
        )
        if not entries:
            raise EntryNotFoundError
        workout_ids = {entry.workout_id for entry in entries}
        for entry in entries:
            await self._session.delete(entry)
        await self._session.flush()
        await self._delete_empty_workouts(workout_ids)
        return len(entries)

    async def delete_entry(self, user: User, entry_id: int) -> date:
        """Delete one entry and return the day it belonged to."""
        row = (
            await self._session.execute(
                select(WorkoutEntry, Workout.day)
                .join(Workout, WorkoutEntry.workout_id == Workout.id)
                .where(Workout.user_id == user.id, WorkoutEntry.id == entry_id)
            )
        ).first()
        if row is None:
            raise EntryNotFoundError
        entry, day = row
        await self._session.delete(entry)
        await self._session.flush()
        await self._delete_empty_workouts({entry.workout_id})
        return day

    async def _exercise(self, user: User, name: str, group: MuscleGroup | None) -> Exercise:
        key = normalize(name)
        exercise = await self._session.scalar(
            select(Exercise).where(Exercise.user_id == user.id, Exercise.key == key)
        )
        if exercise is None:
            exercise = Exercise(
                user_id=user.id, name=name, key=key, muscle_group=group or MuscleGroup.OTHER
            )
            self._session.add(exercise)
            await self._session.flush()
        elif exercise.muscle_group is MuscleGroup.OTHER and group is not None:
            exercise.muscle_group = group  # learn the group once it is known
        return exercise

    async def _find_exercise(self, user: User, query_text: str) -> Exercise:
        key = normalize(query_text)
        if not key:
            raise ExerciseNotFoundError
        candidates = await self.exercises(user)
        exact = next((e for e in candidates if e.key == key), None)
        partial = sorted((e for e in candidates if key in e.key), key=lambda e: len(e.key))
        match = exact or next(iter(partial), None)
        if match is None:
            raise ExerciseNotFoundError
        return match

    async def _delete_empty_workouts(self, workout_ids: set[int]) -> None:
        remaining = set(
            await self._session.scalars(
                select(WorkoutEntry.workout_id).where(WorkoutEntry.workout_id.in_(workout_ids))
            )
        )
        empty = workout_ids - remaining
        if empty:
            await self._session.execute(delete(Workout).where(Workout.id.in_(empty)))
