"""Checks every value the AI returns before the bot acts on it.

The AI only segments and classifies the message; numbers and dates are re-parsed with
the bot's own deterministic parsers, and an amount must exist in what the user wrote.
"""

import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from asistente.ai.schema import ExerciseDone, Movement, ReminderRequest, Target
from asistente.core.dates import parse_day
from asistente.core.money import find_amounts, parse_amount
from asistente.core.text import normalize
from asistente.finance.commands import TargetQuery, parse_target
from asistente.finance.models import TransactionKind
from asistente.finance.parser import ParsedEntry
from asistente.gym.models import MAX_EXERCISE_NAME_LENGTH
from asistente.gym.parser import MAX_REPS, MAX_SETS, ExerciseItem
from asistente.gym.units import parse_kg
from asistente.reminders.parser import ParsedReminder, clean_text, parse_when

MAX_MOVEMENTS = 5
MAX_EXERCISES = 20
MAX_WORDS = 20

_DIGITS = re.compile(r"\d+")
_CLOCK = re.compile(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})")


def safe_amount(text: str | None, message: str) -> int | None:
    """Cents of an amount given by the AI, only if the message backs it up.

    When the user wrote amounts with digits, the AI's amount must be one of them: it may
    not "fix" or invent numbers. Spelled-out amounts ("dos lucas") have no digits to check.
    """
    if not text:
        return None
    try:
        cents = parse_amount(text)
    except ValueError:
        return None
    written = {match.cents for match in find_amounts(message.split())}
    return cents if not written or cents in written else None


def safe_day(text: str | None, today: date) -> date | None:
    return parse_day(text, today) if text else None


def safe_time(text: str | None) -> time | None:
    """A 24h ``HH:MM`` time of day, or ``None``."""
    matched = _CLOCK.fullmatch(text.strip()) if text else None
    if matched is None:
        return None
    hour, minute = int(matched["hour"]), int(matched["minute"])
    return time(hour, minute) if hour < 24 and minute < 60 else None


def to_entry(movement: Movement, message: str, today: date) -> ParsedEntry | None:
    cents = safe_amount(movement.amount, message)
    if cents is None:
        return None
    words = movement.description.split() + (movement.account or "").split()
    return ParsedEntry(
        amount_cents=cents,
        words=tuple(words[:MAX_WORDS]),
        # The AI says which way the money went: "hice una transferencia" is an expense.
        kind=TransactionKind.INCOME if movement.income else TransactionKind.EXPENSE,
        day=safe_day(movement.day, today),
    )


def to_target(target: Target | None, message: str, today: date) -> TargetQuery:
    if target is None:
        return TargetQuery(words=(), amount_cents=None, day=None, latest=False)
    words = parse_target(target.description or "", today).words
    return TargetQuery(
        words=words,
        amount_cents=safe_amount(target.amount, message),
        day=safe_day(target.day, today),
        latest=target.latest,
    )


def to_exercise_items(exercises: list[ExerciseDone], message: str) -> list[ExerciseItem] | None:
    """Exercise items, or ``None`` if any value is out of range or not in the message."""
    numbers = {int(digits) for digits in _DIGITS.findall(message)}
    items = []
    for exercise in exercises[:MAX_EXERCISES]:
        name = " ".join(exercise.name.split())
        if not normalize(name) or len(name) > MAX_EXERCISE_NAME_LENGTH:
            return None
        if not (1 <= exercise.sets <= MAX_SETS and 1 <= exercise.reps <= MAX_REPS):
            return None
        if numbers and not {exercise.sets, exercise.reps} <= numbers:
            return None
        weight_grams = None
        if exercise.weight_kg is not None:
            weight_grams = parse_kg(f"{exercise.weight_kg:g}")
            if weight_grams is None:
                return None
        items.append(
            ExerciseItem(
                name=name[0].upper() + name[1:],
                muscle_group=exercise.muscle_group,
                sets=exercise.sets,
                reps=exercise.reps,
                weight_grams=weight_grams,
            )
        )
    return items or None


def to_reminder(
    request: ReminderRequest | None, now: datetime, tz: ZoneInfo
) -> ParsedReminder | None:
    """The reminder, if the bot's own parser understands the whole timing the AI wrote."""
    if request is None:
        return None
    when = parse_when(request.when, now, tz)
    text = clean_text(request.text)
    if when is None or not text:
        return None
    return ParsedReminder(
        text=text, schedule=when.schedule, first_run=when.first_run, timezone=when.timezone
    )
