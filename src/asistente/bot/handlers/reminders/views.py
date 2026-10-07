"""Reminder texts (HTML), the Argentine way: 24 h clock, dd/mm dates, "a las 9:00".

The reminder text comes from the user, so it is always escaped.
"""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from html import escape
from zoneinfo import ZoneInfo

from asistente.core.schedule import WEEKEND, WORKDAYS, Repeat, Schedule
from asistente.reminders.models import Reminder
from asistente.reminders.parser import is_late_night

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
EMPTY_LIST = (
    "⏰ No tenés recordatorios.\nCreá uno así: <code>recordame mañana a las 9 pagar la luz</code>"
)
_LIST_TITLE_LENGTH = 60  # 30 reminders still fit in one message


def created(reminder: Reminder, tz: ZoneInfo, *, now: datetime) -> str:
    today = now.astimezone(tz).date()
    # Late at night "hoy" and "mañana" are easy to misread: the date says which day it is.
    dated = is_late_night(now, tz)
    lines = [f"⏰ <b>Te lo recuerdo:</b> {title(reminder)}", when(reminder, today, dated=dated)]
    if (other := other_zone(reminder, tz, today)) is not None:
        lines.append(other)
    return "\n".join(lines)


def reminder_list(reminders: Sequence[Reminder], tz: ZoneInfo, *, now: datetime) -> str:
    if not reminders:
        return EMPTY_LIST
    today = now.astimezone(tz).date()
    lines = ["⏰ <b>Tus recordatorios</b>", ""]
    for number, reminder in enumerate(reminders, start=1):
        name = title(reminder)
        if len(reminder.text) > _LIST_TITLE_LENGTH:
            name = escape(reminder.text[:1].upper() + reminder.text[1:_LIST_TITLE_LENGTH]) + "…"
        zone = "" if reminder.timezone == tz.key else f" · hora de {zone_label(reminder.timezone)}"
        lines += [f"{number}. <b>{name}</b>", f"    {when(reminder, today)}{zone}"]
    lines += ["", "Tocá 🗑 para borrar uno."]
    return "\n".join(lines)


def fired(reminder: Reminder, tz: ZoneInfo, *, now: datetime, late: bool) -> str:
    """The reminder itself, as it arrives (and notifies) when it is due."""
    lines = [f"⏰ <b>{title(reminder)}</b>"]
    if late:
        due = run_label(reminder.next_run_at.astimezone(tz), now.astimezone(tz).date())
        lines.append(f"<i>Era para {due}: el bot estaba apagado.</i>")
    return "\n".join(lines)


def done(reminder: Reminder) -> str:
    return f"✅ <s>{title(reminder)}</s>"


def snoozed(copy: Reminder, tz: ZoneInfo) -> str:
    again = at_label(copy.next_run_at.astimezone(tz).time())
    return f"⏳ {title(copy)}\nTe lo vuelvo a recordar {again}."


def title(reminder: Reminder) -> str:
    return escape(reminder.text[:1].upper() + reminder.text[1:])


def when(reminder: Reminder, today: date, *, dated: bool = False) -> str:
    """``📅 mañana a las 9:00`` or ``🔁 todos los lunes a las 12:00 · próximo: hoy``.

    ``dated`` adds the date to "hoy" and "mañana": ``📅 hoy (mar 06/10) a las 9:00``.
    """
    run = reminder.next_run_at.astimezone(reminder.zone)
    if reminder.repeat is Repeat.ONCE:
        return f"📅 {run_label(run, today, dated=dated)}"
    next_day = day_label(run.date(), today, dated=dated)
    return f"🔁 {schedule_label(reminder.schedule)} · próximo: {next_day}"


def other_zone(reminder: Reminder, tz: ZoneInfo, today: date) -> str | None:
    """``🌍 hora de Madrid · acá: mañana a las 5:00`` for a reminder in another time zone."""
    if reminder.timezone == tz.key:
        return None
    here = run_label(reminder.next_run_at.astimezone(tz), today)
    return f"🌍 hora de {zone_label(reminder.timezone)} · acá: {here}"


def run_label(run: datetime, today: date, *, dated: bool = False) -> str:
    return f"{day_label(run.date(), today, dated=dated)} {at_label(run.time())}"


def day_label(day: date, today: date, *, dated: bool = False) -> str:
    """``hoy``, ``mañana`` or ``el mié 15/10``; ``dated`` gives ``hoy (lun 05/10)``."""
    for name, offset in (("hoy", 0), ("mañana", 1)):
        if day == today + timedelta(days=offset):
            return f"{name} ({_short_date(day)})" if dated else name
    label = f"el {_short_date(day)}"
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


def _short_date(day: date) -> str:
    return f"{WEEKDAYS_SHORT[day.weekday()]} {day:%d/%m}"


def _join(words: Sequence[str]) -> str:
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} y {words[-1]}"
