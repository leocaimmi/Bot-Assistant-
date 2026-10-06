from collections.abc import Callable
from datetime import datetime, time

import pytest

from asistente.reminders.schedule import (
    WORKDAYS,
    Repeat,
    Schedule,
    mask_to_weekdays,
    next_occurrence,
    weekdays_to_mask,
)
from tests.factories import BUENOS_AIRES

# Monday 5 October 2026, 10:00 in Buenos Aires.
NOW = datetime(2026, 10, 5, 10, 0, tzinfo=BUENOS_AIRES)


def _at(day: int, hour: int, minute: int = 0, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=BUENOS_AIRES)


@pytest.mark.parametrize(
    ("schedule", "expected"),
    [
        (Schedule(Repeat.DAILY, time(12, 0)), _at(5, 12)),
        (Schedule(Repeat.DAILY, time(8, 0)), _at(6, 8)),
        (Schedule(Repeat.DAILY, time(10, 0)), _at(6, 10)),  # strictly after
        (Schedule(Repeat.WEEKLY, time(12, 0), weekdays=frozenset({0})), _at(5, 12)),
        (Schedule(Repeat.WEEKLY, time(9, 0), weekdays=frozenset({0})), _at(12, 9)),
        (Schedule(Repeat.WEEKLY, time(20, 0), weekdays=frozenset({3, 5})), _at(8, 20)),
        (Schedule(Repeat.WEEKLY, time(7, 0), weekdays=WORKDAYS), _at(6, 7)),
        (Schedule(Repeat.MONTHLY, time(9, 0), day_of_month=10), _at(10, 9)),
        (Schedule(Repeat.MONTHLY, time(9, 0), day_of_month=5), _at(5, 9, month=11)),
        # 31 runs on the last day of shorter months.
        (Schedule(Repeat.MONTHLY, time(9, 0), day_of_month=31), _at(31, 9)),
    ],
)
def test_next_occurrence(schedule: Schedule, expected: datetime) -> None:
    assert next_occurrence(schedule, NOW) == expected


def test_day_31_in_a_short_month() -> None:
    schedule = Schedule(Repeat.MONTHLY, time(9, 0), day_of_month=31)

    assert next_occurrence(schedule, _at(1, 0, month=11)) == _at(30, 9, month=11)


def test_once_has_no_next_occurrence() -> None:
    assert next_occurrence(Schedule(Repeat.ONCE, time(9, 0)), NOW) is None


@pytest.mark.parametrize(
    "build",
    [
        lambda: Schedule(Repeat.WEEKLY, time(9, 0)),
        lambda: Schedule(Repeat.WEEKLY, time(9, 0), weekdays=frozenset({7})),
        lambda: Schedule(Repeat.DAILY, time(9, 0), weekdays=frozenset({1})),
        lambda: Schedule(Repeat.MONTHLY, time(9, 0)),
        lambda: Schedule(Repeat.MONTHLY, time(9, 0), day_of_month=32),
        lambda: Schedule(Repeat.ONCE, time(9, 0), day_of_month=3),
    ],
)
def test_rejects_inconsistent_schedules(build: Callable[[], Schedule]) -> None:
    with pytest.raises(ValueError, match=r"weekdays|day of the month"):
        build()


def test_weekday_mask_round_trip() -> None:
    weekdays = frozenset({0, 3, 6})

    assert weekdays_to_mask(weekdays) == 0b1001001
    assert mask_to_weekdays(weekdays_to_mask(weekdays)) == weekdays
