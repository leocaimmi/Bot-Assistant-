"""When a reminder fires: once, every day, on some weekdays or on a day of every month.

Everything here works in the user's local time; the database keeps the next run in UTC.
"""

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum

WORKDAYS = frozenset(range(5))
WEEKEND = frozenset({5, 6})
# Every schedule that repeats runs at least once in this many days (monthly: 31st of Feb...).
_SEARCH_DAYS = 70


class Repeat(StrEnum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass(frozen=True, slots=True)
class Schedule:
    repeat: Repeat
    at: time  # local time of day
    weekdays: frozenset[int] = frozenset()  # WEEKLY only: 0 is Monday
    day_of_month: int | None = None  # MONTHLY only: 1-31; the last day in shorter months

    def __post_init__(self) -> None:
        weekly = self.repeat is Repeat.WEEKLY
        if weekly != bool(self.weekdays) or not self.weekdays <= frozenset(range(7)):
            raise ValueError("only weekly schedules have weekdays, between 0 and 6")
        if self.repeat is Repeat.MONTHLY:
            if self.day_of_month is None or not 1 <= self.day_of_month <= 31:
                raise ValueError("monthly schedules need a day of the month between 1 and 31")
        elif self.day_of_month is not None:
            raise ValueError("only monthly schedules have a day of the month")


def next_occurrence(schedule: Schedule, after: datetime) -> datetime | None:
    """First run strictly after ``after`` (aware, local time); ``None`` for ONCE."""
    if schedule.repeat is Repeat.ONCE:
        return None
    day = after.date()
    for _ in range(_SEARCH_DAYS):
        if _runs_on(schedule, day):
            candidate = datetime.combine(day, schedule.at, tzinfo=after.tzinfo)
            if candidate > after:
                return candidate
        day += timedelta(days=1)
    raise ValueError(f"{schedule} never runs")


def weekdays_to_mask(weekdays: frozenset[int]) -> int:
    return sum(1 << day for day in weekdays)


def mask_to_weekdays(mask: int) -> frozenset[int]:
    return frozenset(day for day in range(7) if mask & (1 << day))


def _runs_on(schedule: Schedule, day: date) -> bool:
    match schedule.repeat:
        case Repeat.DAILY:
            return True
        case Repeat.WEEKLY:
            return day.weekday() in schedule.weekdays
        case Repeat.MONTHLY:
            last_day = calendar.monthrange(day.year, day.month)[1]
            return day.day == min(schedule.day_of_month or 1, last_day)
        case Repeat.ONCE:
            return False
