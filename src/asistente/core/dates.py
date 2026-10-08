"""Dates in the user's timezone, with Spanish month names and relative days."""

import re
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from asistente.core.text import normalize

# Years the bot accepts: keeps typos and forged input away from date arithmetic.
MIN_YEAR = 2000
MAX_YEAR = 2100

MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

_MONTH_NUMBERS: dict[str, int] = {
    **{name: number for number, name in enumerate(MONTHS, start=1)},
    **{name[:3]: number for number, name in enumerate(MONTHS, start=1)},
    "setiembre": 9,
    "set": 9,
}

_RELATIVE_DAYS = {"hoy": 0, "ayer": 1, "anteayer": 2}
_WEEKDAYS = {
    name: number
    for number, name in enumerate(
        ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
    )
}

_DAY_PATTERN = re.compile(r"(?P<day>\d{1,2})/(?P<month>\d{1,2})(?:/(?P<year>\d{2}|\d{4}))?")
_NUMERIC_MONTH_PATTERN = re.compile(r"(?P<month>\d{1,2})(?:[/-](?P<year>\d{2}|\d{4}))?")
_ISO_MONTH_PATTERN = re.compile(r"(?P<year>\d{4})-(?P<month>\d{1,2})")


def month_label(year: int, month: int) -> str:
    """``(2026, 10)`` -> ``'octubre 2026'``."""
    return f"{MONTHS[month - 1]} {year}"


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def month_range(year: int, month: int, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """UTC bounds ``[start, end)`` of a calendar month in the user's timezone."""
    next_year, next_month = shift_month(year, month, 1)
    start = datetime(year, month, 1, tzinfo=tz)
    end = datetime(next_year, next_month, 1, tzinfo=tz)
    return start.astimezone(UTC), end.astimezone(UTC)


def parse_month(text: str, today: date) -> tuple[int, int] | None:
    """Read a month: ``septiembre``, ``sep 2025``, ``9``, ``09/2026``, ``2026-09``.

    Without a year, it is the latest such month that is not in the future.
    """
    words = normalize(text).split()
    raw = text.strip()

    if len(words) in (1, 2) and words[0] in _MONTH_NUMBERS:
        month = _MONTH_NUMBERS[words[0]]
        if len(words) == 1:
            return _latest(month, today), month
        year = _year(words[1])
        return (year, month) if year is not None else None

    for pattern in (_ISO_MONTH_PATTERN, _NUMERIC_MONTH_PATTERN):
        matched = pattern.fullmatch(raw)
        if matched is None:
            continue
        month = int(matched["month"])
        if not 1 <= month <= 12:
            return None
        if matched["year"] is None:
            return _latest(month, today), month
        year = _year(matched["year"])
        return (year, month) if year is not None else None
    return None


def parse_day(text: str, today: date) -> date | None:
    """Read a day: ``hoy``, ``ayer``, ``anteayer``, ``el miércoles``, ``15/09`` or ``15/09/2026``.

    A weekday is the latest one, today included; ``dd/mm`` without a year is the latest
    such date that is not in the future.
    """
    word = normalize(text).removeprefix("el ")
    if word in _RELATIVE_DAYS:
        return today - timedelta(days=_RELATIVE_DAYS[word])
    if word in _WEEKDAYS:
        return today - timedelta(days=(today.weekday() - _WEEKDAYS[word]) % 7)

    matched = _DAY_PATTERN.fullmatch(text.strip())
    if matched is None:
        return None
    day, month = int(matched["day"]), int(matched["month"])
    year = _year(matched["year"]) if matched["year"] else today.year
    if year is None:
        return None
    try:
        parsed = date(year, month, day)
    except ValueError:
        return None
    if matched["year"] is None and parsed > today:
        try:
            parsed = parsed.replace(year=year - 1)
        except ValueError:  # 29/02 of a non-leap year
            return None
    return parsed


def at_local_time(day: date, clock: time, tz: ZoneInfo) -> datetime:
    """Aware datetime for ``day`` at ``clock`` in the user's timezone."""
    return datetime.combine(day, clock, tzinfo=tz)


def format_datetime(moment: datetime, tz: ZoneInfo) -> str:
    """``'05/10/2026 14:32'`` in the user's timezone."""
    return moment.astimezone(tz).strftime("%d/%m/%Y %H:%M")


def format_short_datetime(moment: datetime, tz: ZoneInfo) -> str:
    """``'05/10 14:32'`` in the user's timezone."""
    return moment.astimezone(tz).strftime("%d/%m %H:%M")


def _latest(month: int, today: date) -> int:
    return today.year if month <= today.month else today.year - 1


def _year(raw: str) -> int | None:
    if not raw.isdigit():
        return None
    year = int(raw)
    if len(raw) == 2:
        year += 2000
    return year if MIN_YEAR <= year <= MAX_YEAR else None
