"""Reminder texts (HTML), the Argentine way: 24 h clock, dd/mm dates, "a las 9:00".

The reminder text comes from the user, so it is always escaped.
"""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from html import escape
from zoneinfo import ZoneInfo

from asistente.reminders.models import Reminder
from asistente.reminders.schedule import WEEKEND, WORKDAYS, Repeat, Schedule

WEEKDAYS_SHORT = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
_WEEKDAYS_PLURAL = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábados", "domingos")

NOT_UNDERSTOOD = (
    "🤔 No entendí cuándo. Probá así:\n"
    "<code>recordame mañana a las 9 pagar la luz</code>\n"
    "<code>recordame todos los lunes a las 12 la pastilla</code>\n"
    "<code>recordame en 20 minutos sacar la ropa</code>"
)
USE_THE_LIST = "⏰ Para ver o borrar recordatorios usá /recordatorios."
DELETED = "🗑 Recordatorio borrado."


def created(reminder: Reminder, tz: ZoneInfo, *, now: datetime) -> str:
    today = now.astimezone(tz).date()
    lines = [f"⏰ <b>Te lo recuerdo:</b> {title(reminder)}", when(reminder, today)]
    if (other := other_zone(reminder, tz, today)) is not None:
        lines.append(other)
    return "\n".join(lines)


def title(reminder: Reminder) -> str:
    return escape(reminder.text[:1].upper() + reminder.text[1:])


def when(reminder: Reminder, today: date) -> str:
    """``📅 mañana a las 9:00`` or ``🔁 todos los lunes a las 12:00 · próximo: hoy``."""
    run = reminder.next_run_at.astimezone(reminder.zone)
    if reminder.repeat is Repeat.ONCE:
        return f"📅 {run_label(run, today)}"
    return f"🔁 {schedule_label(reminder.schedule)} · próximo: {day_label(run.date(), today)}"


def other_zone(reminder: Reminder, tz: ZoneInfo, today: date) -> str | None:
    """``🌍 hora de Madrid · acá: mañana a las 5:00`` for a reminder in another time zone."""
    if reminder.timezone == tz.key:
        return None
    here = run_label(reminder.next_run_at.astimezone(tz), today)
    return f"🌍 hora de {zone_label(reminder.timezone)} · acá: {here}"


def run_label(run: datetime, today: date) -> str:
    return f"{day_label(run.date(), today)} {at_label(run.time())}"


def day_label(day: date, today: date) -> str:
    if day == today:
        return "hoy"
    if day == today + timedelta(days=1):
        return "mañana"
    label = f"el {WEEKDAYS_SHORT[day.weekday()]} {day:%d/%m}"
    return label if day.year == today.year else f"{label}/{day.year}"


def at_label(clock: time) -> str:
    """``a las 9:00``, ``a la 1:30`` (24 h)."""
    article = "a la" if clock.hour == 1 else "a las"
    return f"{article} {clock.hour}:{clock.minute:02d}"


def schedule_label(schedule: Schedule) -> str:
    at = at_label(schedule.at)
    match schedule.repeat:
        case Repeat.DAILY:
            return f"todos los días {at}"
        case Repeat.WEEKLY:
            if schedule.weekdays == WORKDAYS:
                return f"de lunes a viernes {at}"
            if schedule.weekdays == WEEKEND:
                return f"los sábados y domingos {at}"
            names = [_WEEKDAYS_PLURAL[day] for day in sorted(schedule.weekdays)]
            return f"todos los {_join(names)} {at}"
        case Repeat.MONTHLY:
            return f"el {schedule.day_of_month} de cada mes {at}"
        case Repeat.ONCE:
            return at


def zone_label(name: str) -> str:
    """``Europe/Madrid`` -> ``Madrid``; ``Etc/GMT+5`` -> ``UTC-5`` (POSIX signs are inverted)."""
    if name.startswith("Etc/GMT"):
        offset = name.removeprefix("Etc/GMT")
        return f"UTC{'-' if offset.startswith('+') else '+'}{offset[1:]}"
    return name.rsplit("/", 1)[-1].replace("_", " ")


def _join(words: Sequence[str]) -> str:
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} y {words[-1]}"
