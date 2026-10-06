"""Reads reminders written the Argentine way: "recordame mañana a las 9 pagar la luz".

A reminder starts with a verb ("recordame", "avisame"...). Its timing can be:

- a day: "hoy", "mañana", "pasado mañana", "el lunes", "15/10", "el 15 de octubre",
  "el 15", "en 3 días";
- an hour, 24 h: "a las 9", "a las 18:30", "a las 8 de la noche", "a las 9 y media",
  "21 hs", "a la tarde", "al mediodía";
- a delay: "en 20 minutos", "en 2 horas", "en media hora";
- a repetition: "todos los días", "los lunes y jueves", "de lunes a viernes", "los fines
  de semana", "el 10 de cada mes", "todos los 10";
- another time zone, only if said: "hora de España", "hora de Miami", "UTC-5".

Whatever is left is what to remember. Without an hour it is 9:00. Days such as "mañana"
count from the user's own date; the hour is in the time zone of the reminder.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from asistente.core.dates import MAX_YEAR, MIN_YEAR, MONTHS
from asistente.core.text import fold
from asistente.reminders.schedule import WEEKEND, WORKDAYS, Repeat, Schedule, next_occurrence

DEFAULT_TIME = time(9, 0)
# Longer messages are not read by the rules (a reminder is a sentence, not an essay).
MAX_MESSAGE_LENGTH = 1000

# Places named for another time zone ("hora de España", "hora española"), folded.
TIME_ZONES: dict[str, str] = {
    "argentina": "America/Argentina/Buenos_Aires",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "espana": "Europe/Madrid",
    "espanola": "Europe/Madrid",
    "madrid": "Europe/Madrid",
    "barcelona": "Europe/Madrid",
    "miami": "America/New_York",
    "nueva york": "America/New_York",
    "new york": "America/New_York",
    "estados unidos": "America/New_York",
    "eeuu": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "california": "America/Los_Angeles",
    "mexico": "America/Mexico_City",
    "mexicana": "America/Mexico_City",
    "chile": "America/Santiago",
    "chilena": "America/Santiago",
    "santiago": "America/Santiago",
    "uruguay": "America/Montevideo",
    "uruguaya": "America/Montevideo",
    "montevideo": "America/Montevideo",
    "brasil": "America/Sao_Paulo",
    "brasilera": "America/Sao_Paulo",
    "brasilena": "America/Sao_Paulo",
    "san pablo": "America/Sao_Paulo",
    "sao paulo": "America/Sao_Paulo",
    "colombia": "America/Bogota",
    "colombiana": "America/Bogota",
    "bogota": "America/Bogota",
    "peru": "America/Lima",
    "peruana": "America/Lima",
    "lima": "America/Lima",
    "paraguay": "America/Asuncion",
    "bolivia": "America/La_Paz",
    "venezuela": "America/Caracas",
    "londres": "Europe/London",
    "inglaterra": "Europe/London",
    "inglesa": "Europe/London",
    "reino unido": "Europe/London",
    "portugal": "Europe/Lisbon",
    "lisboa": "Europe/Lisbon",
    "francia": "Europe/Paris",
    "francesa": "Europe/Paris",
    "paris": "Europe/Paris",
    "italia": "Europe/Rome",
    "italiana": "Europe/Rome",
    "roma": "Europe/Rome",
    "alemania": "Europe/Berlin",
    "alemana": "Europe/Berlin",
    "berlin": "Europe/Berlin",
    "japon": "Asia/Tokyo",
    "tokio": "Asia/Tokyo",
    "china": "Asia/Shanghai",
    "australia": "Australia/Sydney",
    "sidney": "Australia/Sydney",
    "sydney": "Australia/Sydney",
}

_PERIOD_TIMES = {"manana": time(9, 0), "tarde": time(15, 0), "noche": time(21, 0)}
_WEEKDAYS = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "domingo": 6,
}
_MONTHS = {name: number for number, name in enumerate(MONTHS, start=1)} | {"setiembre": 9}
_UNIT_MINUTES = {"min": 1, "minuto": 1, "hora": 60, "hs": 60, "dia": 1440}
_DAY = r"(?:lunes|martes|miercoles|jueves|viernes|sabados?|domingos?)"

_VERB = re.compile(
    r"\b(?:recordame|recordarme|recorda|recuerdame|acordame|avisame|recordatorio)\b[\s,:]*"
)
# The place is a lookahead: an unknown one ("hora de comer") stays in the text, and two
# zones in a row ("hora de España hora de Chile") are both found.
_ZONE = re.compile(
    r"\b(?:en\s+)?(?:hora|horario)\s+(?:de\s+(?:la\s+|el\s+)?)?"
    r"(?=(?P<place>[a-z]+(?:\s+[a-z]+)?))"
)
_OFFSET = re.compile(r"\b(?:hora\s+)?(?:utc|gmt)(?:\s*(?P<sign>[+-])\s*(?P<hours>\d{1,2}))?\b")
_DELAY = re.compile(
    r"\ben\s+(?P<amount>\d{1,3}|un|una|media)\s+(?P<unit>minutos?|mins?|horas?|hs|dias?)\b"
)
_DAILY = re.compile(
    r"\b(?:todos\s+los\s+dias|cada\s+dia|diariamente"
    r"|todas\s+las\s+(?P<period>manana|tarde|noche)s)\b"
)
_WORKDAYS = re.compile(
    r"\b(?:de\s+lunes\s+a\s+viernes|(?:todos\s+los\s+|los\s+)?dias\s+(?:de\s+semana|habiles))\b"
)
_WEEKENDS = re.compile(r"\b(?:todos\s+los|cada|los)\s+fines?\s+de\s+semana\b")
_WEEKLY = re.compile(
    rf"\b(?:todos\s+los|cada|los)\s+(?P<days>{_DAY}(?:\s*(?:,|y|e)\s*(?:los\s+)?{_DAY})*)\b"
)
_MONTHLY = re.compile(
    r"\b(?:el\s+)?(?P<a>\d{1,2})\s+de\s+cada\s+mes\b"
    r"|\b(?:todos\s+los\s+meses|cada\s+mes)\s+el\s+(?P<b>\d{1,2})\b"
    r"|\btodos\s+los\s+(?P<c>\d{1,2})\b(?!\s*(?:minutos?|horas?|dias?|meses))"
)
_AT = re.compile(
    r"\ba\s+las?\s+(?P<hour>\d{1,2})(?:[:.](?P<minute>\d{2}))?"
    r"(?:\s+y\s+(?P<fraction>media|cuarto))?(?:\s*(?:hs|h|horas?)\b)?"
    r"(?:\s*(?P<ampm>am|pm)\b)?"
    r"(?:\s+(?:de\s+la\s+(?P<period>manana|tarde|noche|madrugada)|(?P<noon>del\s+mediodia)))?\b"
)
_CLOCK = re.compile(
    r"\b(?P<hour>\d{1,2}):(?P<minute>\d{2})(?:\s*(?:hs|h)\b)?(?:\s*(?P<ampm>am|pm)\b)?"
)
_HOURS = re.compile(r"\b(?P<hour>\d{1,2})\s*(?:hs|h)\b")
_THIS_PERIOD = re.compile(r"\besta\s+(?P<period>manana|tarde|noche)\b")
_PERIOD = re.compile(r"\b(?:a|por|en)\s+la\s+(?P<period>manana|tarde|noche)\b|\bal\s+mediodia\b")
_AFTER_TOMORROW = re.compile(r"\bpasado\s+manana\b")
_TOMORROW = re.compile(r"\bmanana\b")
_TODAY = re.compile(r"\bhoy\b")
_DATE = re.compile(r"\b(?:el\s+)?(?P<day>\d{1,2})/(?P<month>\d{1,2})(?:/(?P<year>\d{4}|\d{2}))?\b")
_DATE_NAMED = re.compile(
    rf"\b(?:el\s+)?(?P<day>\d{{1,2}})\s+de\s+(?P<month>{'|'.join(_MONTHS)})"
    r"(?:\s+(?:de\s+|del\s+)?(?P<year>\d{4}))?\b"
)
_WEEKDAY = re.compile(
    r"\b(?:el\s+)?(?:proximo\s+)?(?P<weekday>lunes|martes|miercoles|jueves|viernes|sabado|domingo)"
    r"(?:\s+que\s+viene|\s+proximo)?\b"
)
_DAY_OF_MONTH = re.compile(r"\bel\s+(?P<day>\d{1,2})\b(?![/:.]\d)")
_LEADING_WORDS = re.compile(r"^(?:(?:que|de|para)\s+)+", re.IGNORECASE)


class _UnclearError(Exception):
    """The timing is ambiguous or impossible: let the AI or the user say it again."""


@dataclass(frozen=True, slots=True)
class ParsedReminder:
    text: str  # what to remember; may be empty
    schedule: Schedule
    first_run: datetime  # aware, in ``timezone``
    timezone: str  # IANA name


@dataclass(frozen=True, slots=True)
class When:
    schedule: Schedule
    first_run: datetime
    timezone: str


def is_reminder_request(text: str) -> bool:
    return _VERB.search(fold(text)) is not None


def mentions_reminders(text: str) -> bool:
    """Whether the text talks about reminders, which are managed from /recordatorios."""
    return "recordatorio" in fold(text)


def parse_reminder(text: str, now: datetime, tz: ZoneInfo) -> ParsedReminder | None:
    """The reminder in ``text``, or ``None`` if its timing is missing or unclear.

    ``now`` is aware and ``tz`` is the user's own time zone.
    """
    if len(text) > MAX_MESSAGE_LENGTH:
        return None
    message = _Message(text)
    if not message.take(_VERB):
        return None
    try:
        when = _read_when(message, now, tz)
    except _UnclearError:
        return None
    return ParsedReminder(
        text=clean_text(message.rest()),
        schedule=when.schedule,
        first_run=when.first_run,
        timezone=when.timezone,
    )


def parse_when(text: str, now: datetime, tz: ZoneInfo) -> When | None:
    """Only a timing ("todos los lunes a las 12"), as the AI rewrites it; else ``None``."""
    if len(text) > MAX_MESSAGE_LENGTH:
        return None
    message = _Message(text)
    try:
        when = _read_when(message, now, tz)
    except _UnclearError:
        return None
    return None if clean_text(message.rest()) else when


def clean_text(text: str) -> str:
    """What to remember, without connectors left at the start ("que", "de", "para")."""
    text = " ".join(text.split()).strip(" ,.;:-")
    return _LEADING_WORDS.sub("", text).strip(" ,.;:-")


class _Message:
    """The text, with the parts already understood blanked out (positions never move)."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.folded = "".join(folded if len(folded := fold(char)) == 1 else char for char in text)
        self._used = [False] * len(text)

    def take(self, pattern: re.Pattern[str]) -> list[re.Match[str]]:
        matches = list(pattern.finditer(self.folded))
        for match in matches:
            self.blank(match.start(), match.end())
        return matches

    def blank(self, start: int, end: int) -> None:
        self.folded = f"{self.folded[:start]}{' ' * (end - start)}{self.folded[end:]}"
        for index in range(start, end):
            self._used[index] = True

    def rest(self) -> str:
        return "".join(
            " " if used else char for char, used in zip(self.text, self._used, strict=True)
        )


@dataclass(slots=True)
class _Parts:
    """What the message says about the timing, before resolving it."""

    delay: timedelta | None = None
    repeat: Repeat | None = None
    weekdays: frozenset[int] = frozenset()
    day_of_month: int | None = None
    clock: tuple[int, int, str | None] | None = None  # hour, minute, am/pm
    period: str | None = None  # manana, tarde, noche, madrugada or noon
    day: date | None = None
    monthly_day: int | None = None  # "el 15": the next 15th


def _read_when(message: _Message, now: datetime, tz: ZoneInfo) -> When:
    zone = ZoneInfo(_take_zone(message) or tz.key)
    today = now.astimezone(tz).date()
    parts = _Parts()
    _take_delay(message, parts, today)
    _take_repetition(message, parts)
    _take_time(message, parts, today)
    _take_day(message, parts, today)
    return _resolve(parts, now, zone)


def _take_zone(message: _Message) -> str | None:
    found: list[str] = []
    for match in _ZONE.finditer(message.folded):
        words = match["place"].split()
        for size in (2, 1):
            name = " ".join(words[:size])
            if len(words) >= size and name in TIME_ZONES:
                message.blank(match.start(), match.start("place") + len(name))
                found.append(TIME_ZONES[name])
                break
    for match in message.take(_OFFSET):
        hours = int(match["hours"] or 0)
        if hours > 14:
            raise _UnclearError
        sign = "-" if match["sign"] == "+" else "+"  # POSIX: Etc/GMT+3 is UTC-3
        found.append(f"Etc/GMT{sign}{hours}" if hours else "UTC")
    if len(found) > 1:
        raise _UnclearError
    if not found:
        return None
    try:
        ZoneInfo(found[0])
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise _UnclearError from exc
    return found[0]


def _take_delay(message: _Message, parts: _Parts, today: date) -> None:
    matches = message.take(_DELAY)
    if not matches:
        return
    if len(matches) > 1:
        raise _UnclearError
    match = matches[0]
    raw = match["amount"]
    amount = {"un": 1, "una": 1, "media": 0.5}.get(raw) or int(raw)
    unit = match["unit"].rstrip("s") if match["unit"] != "hs" else "hs"
    minutes = amount * _UNIT_MINUTES[unit]
    if minutes <= 0:
        raise _UnclearError
    if unit == "dia":
        parts.day = today + timedelta(days=int(amount))
    else:
        parts.delay = timedelta(minutes=minutes)


def _take_repetition(message: _Message, parts: _Parts) -> None:
    found: list[tuple[Repeat, frozenset[int], int | None]] = []
    for match in message.take(_DAILY):
        found.append((Repeat.DAILY, frozenset(), None))
        _set_period(parts, match["period"])
    found += [(Repeat.WEEKLY, WORKDAYS, None) for _ in message.take(_WORKDAYS)]
    found += [(Repeat.WEEKLY, WEEKEND, None) for _ in message.take(_WEEKENDS)]
    for match in message.take(_WEEKLY):
        days = frozenset(_WEEKDAYS[_singular(name)] for name in re.findall(_DAY, match["days"]))
        found.append((Repeat.WEEKLY, days, None))
    for match in message.take(_MONTHLY):
        day = int(match["a"] or match["b"] or match["c"])
        if not 1 <= day <= 31:
            raise _UnclearError
        found.append((Repeat.MONTHLY, frozenset(), day))
    if len(found) > 1:
        raise _UnclearError
    if found:
        parts.repeat, parts.weekdays, parts.day_of_month = found[0]


def _take_time(message: _Message, parts: _Parts, today: date) -> None:
    clocks = message.take(_AT) + message.take(_CLOCK) + message.take(_HOURS)
    if len(clocks) > 1:
        raise _UnclearError
    if clocks:
        match = clocks[0]
        groups = match.groupdict()
        minute = int(groups.get("minute") or 0)
        if groups.get("fraction"):
            minute = 30 if groups["fraction"] == "media" else 15
        parts.clock = (int(match["hour"]), minute, groups.get("ampm"))
        _set_period(parts, groups.get("period") or ("noon" if groups.get("noon") else None))
    for match in message.take(_THIS_PERIOD):
        _set_day(parts, today)
        _set_period(parts, match["period"])
    for match in message.take(_PERIOD):
        _set_period(parts, match["period"] or "noon")


def _take_day(message: _Message, parts: _Parts, today: date) -> None:
    for _ in message.take(_AFTER_TOMORROW):
        _set_day(parts, today + timedelta(days=2))
    for _ in message.take(_TOMORROW):
        _set_day(parts, today + timedelta(days=1))
    for _ in message.take(_TODAY):
        _set_day(parts, today)
    for match in message.take(_DATE):
        _set_day(parts, _next_date(today, int(match["day"]), int(match["month"]), match["year"]))
    for match in message.take(_DATE_NAMED):
        month = _MONTHS[match["month"]]
        _set_day(parts, _next_date(today, int(match["day"]), month, match["year"]))
    for match in message.take(_WEEKDAY):
        ahead = (_WEEKDAYS[match["weekday"]] - today.weekday()) % 7 or 7
        _set_day(parts, today + timedelta(days=ahead))
    for match in message.take(_DAY_OF_MONTH):
        if parts.day is not None or parts.monthly_day is not None:
            raise _UnclearError
        parts.monthly_day = int(match["day"])
        if not 1 <= parts.monthly_day <= 31:
            raise _UnclearError


def _resolve(parts: _Parts, now: datetime, zone: ZoneInfo) -> When:
    has_day = parts.day is not None or parts.monthly_day is not None
    if parts.delay is not None:
        if parts.repeat or parts.clock or parts.period or has_day:
            raise _UnclearError
        first_run = (now + parts.delay).astimezone(zone)
        return When(Schedule(Repeat.ONCE, first_run.time()), first_run, zone.key)

    at = _at(parts)
    if parts.repeat is not None:
        if has_day:
            raise _UnclearError
        schedule = Schedule(parts.repeat, at, parts.weekdays, parts.day_of_month)
        next_run = next_occurrence(schedule, now.astimezone(zone))
        if next_run is None:  # pragma: no cover - repeating schedules always run again
            raise _UnclearError
        return When(schedule, next_run, zone.key)

    schedule = Schedule(Repeat.ONCE, at)
    if parts.monthly_day is not None:
        return When(schedule, _next_day_of_month(parts.monthly_day, at, now, zone), zone.key)
    if parts.day is not None:
        return When(schedule, datetime.combine(parts.day, at, tzinfo=zone), zone.key)
    if parts.clock is None and parts.period is None:
        raise _UnclearError  # no timing at all
    first_run = datetime.combine(now.astimezone(zone).date(), at, tzinfo=zone)
    if first_run <= now:  # "a las 9" when it is already 10: tomorrow
        first_run += timedelta(days=1)
    return When(schedule, first_run, zone.key)


def _at(parts: _Parts) -> time:
    if parts.clock is None:
        if parts.period == "noon":
            return time(12, 0)
        return _PERIOD_TIMES.get(parts.period, DEFAULT_TIME) if parts.period else DEFAULT_TIME
    hour, minute, ampm = parts.clock
    if ampm == "pm" and hour < 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    elif parts.period in ("tarde", "noche") and hour < 12:
        hour += 12  # "a las 8 de la noche" is 20:00
    elif parts.period == "noche" and hour == 12:
        hour = 0
    elif parts.period == "noon" and hour < 5:
        hour += 12  # "a la 1 del mediodía" is 13:00
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise _UnclearError
    return time(hour, minute)


def _singular(day: str) -> str:
    """Plural weekday names to singular: "sabados" -> "sabado"."""
    return day[:-1] if day in ("sabados", "domingos") else day


def _set_day(parts: _Parts, day: date) -> None:
    if parts.day is not None:
        raise _UnclearError
    parts.day = day


def _set_period(parts: _Parts, period: str | None) -> None:
    if period is None:
        return
    if parts.period is not None and parts.period != period:
        raise _UnclearError
    parts.period = period


def _next_date(today: date, day: int, month: int, raw_year: str | None) -> date:
    """``day/month``, this year or the next one if it already passed."""
    try:
        if raw_year is not None:
            year = int(raw_year) + (2000 if len(raw_year) == 2 else 0)
            if not MIN_YEAR <= year <= MAX_YEAR:
                raise _UnclearError
            return date(year, month, day)
        candidate = date(today.year, month, day)
        return candidate if candidate >= today else date(today.year + 1, month, day)
    except ValueError as exc:  # 31/02
        raise _UnclearError from exc


def _next_day_of_month(day: int, at: time, now: datetime, zone: ZoneInfo) -> datetime:
    """The next time a month has a ``day`` (``el 31`` skips months without one)."""
    local_now = now.astimezone(zone)
    year, month = local_now.year, local_now.month
    for _ in range(13):
        try:
            candidate = datetime.combine(date(year, month, day), at, tzinfo=zone)
        except ValueError:
            candidate = None
        if candidate is not None and candidate > now:
            return candidate
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    raise _UnclearError  # pragma: no cover - every day exists within a year
