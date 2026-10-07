from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from asistente.core.schedule import WORKDAYS, Repeat
from asistente.reminders.parser import (
    clean_text,
    is_late_night,
    is_reminder_request,
    parse_reminder,
    parse_when,
)
from tests.factories import BUENOS_AIRES

# Monday 5 October 2026, 10:00 in Buenos Aires.
NOW = datetime(2026, 10, 5, 10, 0, tzinfo=BUENOS_AIRES)


def _ar(day: int, hour: int, minute: int = 0, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=BUENOS_AIRES)


@pytest.mark.parametrize(
    ("message", "first_run", "text"),
    [
        ("recordame mañana a las 9 pagar la luz", _ar(6, 9), "pagar la luz"),
        (
            "Recordame mañana a las 9 que tengo que pagar la luz.",
            _ar(6, 9),
            "tengo que pagar la luz",
        ),
        ("recordame en 20 minutos sacar la ropa", _ar(5, 10, 20), "sacar la ropa"),
        ("recordame en media hora llamar a mamá", _ar(5, 10, 30), "llamar a mamá"),
        ("recordame en 2 horas", _ar(5, 12), ""),
        ("recordame el 15/10 a las 18:30 turno médico", _ar(15, 18, 30), "turno médico"),
        ("recordame el 15 de octubre a las 8 de la noche turno", _ar(15, 20), "turno"),
        ("recordame el viernes comprar pan", _ar(9, 9), "comprar pan"),
        ("recordame el lunes reunión", _ar(12, 9), "reunión"),  # today is Monday: next one
        ("recordame a las 9 y media llamar al banco", _ar(6, 9, 30), "llamar al banco"),
        ("recordame a las 3 de la tarde", _ar(5, 15), ""),
        ("recordame esta noche ver la serie", _ar(5, 21), "ver la serie"),
        ("recordame pasado mañana a la tarde", _ar(7, 15), ""),
        ("recordame en 3 días renovar el DNI", _ar(8, 9), "renovar el DNI"),
        ("recordame el 15 pagar la tarjeta", _ar(15, 9), "pagar la tarjeta"),
        ("recordame el 5 pagar la tarjeta", _ar(5, 9, month=11), "pagar la tarjeta"),
        ("avisame a las 21 hs que juega boca", _ar(5, 21), "juega boca"),
        ("recordame al mediodía almorzar", _ar(5, 12), "almorzar"),
        ("recordame 1/1 saludar", datetime(2027, 1, 1, 9, tzinfo=BUENOS_AIRES), "saludar"),
    ],
)
def test_once(message: str, first_run: datetime, text: str) -> None:
    parsed = parse_reminder(message, NOW, BUENOS_AIRES)

    assert parsed is not None, message
    assert parsed.schedule.repeat is Repeat.ONCE
    assert parsed.first_run == first_run
    assert parsed.text == text
    assert parsed.timezone == "America/Argentina/Buenos_Aires"


@pytest.mark.parametrize(
    ("message", "repeat", "at", "first_run", "text"),
    [
        (
            "recordame todos los lunes a las 12 que tengo que tomar una pastilla",
            Repeat.WEEKLY,
            time(12, 0),
            _ar(5, 12),
            "tengo que tomar una pastilla",
        ),
        (
            "recordame todos los días a las 8 tomar agua",
            Repeat.DAILY,
            time(8, 0),
            _ar(6, 8),
            "tomar agua",
        ),
        (
            "recordame todas las noches sacar la basura",
            Repeat.DAILY,
            time(21, 0),
            _ar(5, 21),
            "sacar la basura",
        ),
        (
            "recordame de lunes a viernes a las 7 ir al gym",
            Repeat.WEEKLY,
            time(7, 0),
            _ar(6, 7),
            "ir al gym",
        ),
        (
            "recordame los martes y jueves a las 20:00 fútbol",
            Repeat.WEEKLY,
            time(20, 0),
            _ar(6, 20),
            "fútbol",
        ),
        (
            "recordame el 10 de cada mes pagar el alquiler",
            Repeat.MONTHLY,
            time(9, 0),
            _ar(10, 9),
            "pagar el alquiler",
        ),
        (
            "recordame todos los 10 pagar el alquiler",
            Repeat.MONTHLY,
            time(9, 0),
            _ar(10, 9),
            "pagar el alquiler",
        ),
    ],
)
def test_repeating(message: str, repeat: Repeat, at: time, first_run: datetime, text: str) -> None:
    parsed = parse_reminder(message, NOW, BUENOS_AIRES)

    assert parsed is not None, message
    assert (parsed.schedule.repeat, parsed.schedule.at) == (repeat, at)
    assert parsed.first_run == first_run
    assert parsed.text == text


def test_weekdays() -> None:
    workdays = parse_reminder("recordame de lunes a viernes a las 7", NOW, BUENOS_AIRES)
    some = parse_reminder("recordame los martes, jueves y sábados a las 9", NOW, BUENOS_AIRES)

    assert workdays is not None and workdays.schedule.weekdays == WORKDAYS
    assert some is not None and some.schedule.weekdays == frozenset({1, 3, 5})


# Tuesday 6 October 2026, 1:29 in Buenos Aires: the user has not slept yet.
LATE_NIGHT = datetime(2026, 10, 6, 1, 29, tzinfo=BUENOS_AIRES)


@pytest.mark.parametrize(
    ("message", "first_run"),
    [
        ("recordame mañana a las 9 una reunión", _ar(6, 9)),  # in a few hours, not tomorrow
        ("recordame mañana a la tarde", _ar(6, 15)),
        ("recordame pasado mañana a las 9", _ar(7, 9)),
        ("recordame mañana a la 1", _ar(7, 1)),  # 1:00 already passed: the calendar tomorrow
        ("recordame hoy a las 9", _ar(6, 9)),
        ("recordame a las 9", _ar(6, 9)),
        ("recordame el miércoles", _ar(7, 9)),
    ],
)
def test_tomorrow_late_at_night_is_the_coming_morning(message: str, first_run: datetime) -> None:
    parsed = parse_reminder(message, LATE_NIGHT, BUENOS_AIRES)

    assert parsed is not None, message
    assert parsed.first_run == first_run


def test_the_night_ends_at_five() -> None:
    at_five = datetime(2026, 10, 6, 5, 0, tzinfo=BUENOS_AIRES)

    parsed = parse_reminder("recordame mañana a las 9 una reunión", at_five, BUENOS_AIRES)

    assert parsed is not None
    assert parsed.first_run == _ar(7, 9)
    assert is_late_night(at_five - timedelta(minutes=1), BUENOS_AIRES)
    assert not is_late_night(at_five, BUENOS_AIRES)


def test_late_night_counts_in_the_users_time_zone() -> None:
    # 1:29 in Buenos Aires is 4:29 UTC: still the night for the user.
    parsed = parse_reminder(
        "recordame mañana a las 9 una reunión", LATE_NIGHT.astimezone(UTC), BUENOS_AIRES
    )

    assert parsed is not None
    assert parsed.first_run == _ar(6, 9)


def test_the_ai_timing_follows_the_same_rule() -> None:
    when = parse_when("mañana a las 9", LATE_NIGHT, BUENOS_AIRES)

    assert when is not None
    assert when.first_run == _ar(6, 9)


def test_another_time_zone() -> None:
    parsed = parse_reminder(
        "Recordame mañana a las 10 hora de España llamar a Pablo", NOW, BUENOS_AIRES
    )

    assert parsed is not None
    assert parsed.timezone == "Europe/Madrid"
    assert parsed.first_run == datetime(2026, 10, 6, 10, tzinfo=ZoneInfo("Europe/Madrid"))
    assert parsed.first_run == _ar(6, 5)  # 10:00 in Madrid is 5:00 in Buenos Aires
    assert parsed.text == "llamar a Pablo"


def test_utc_offset() -> None:
    parsed = parse_reminder("recordame mañana a las 9 UTC-5 la call", NOW, BUENOS_AIRES)

    assert parsed is not None
    assert parsed.timezone == "Etc/GMT+5"
    assert parsed.first_run == _ar(6, 11)


@pytest.mark.parametrize(
    "message",
    [
        "recordame pagar la luz",  # no timing
        "recordame a la hora de comer la pastilla",  # "hora de comer" is not a time zone
        "recordame mañana y el lunes",
        "recordame todos los lunes a partir de mañana",
        "recordame en 20 minutos a las 9",
        "recordame el 31/02",
        "recordame a las 25",
        "recordame mañana hora de España hora de Chile",
        "uber 2000",
    ],
)
def test_unclear_timing(message: str) -> None:
    assert parse_reminder(message, NOW, BUENOS_AIRES) is None


def test_parse_when_only_accepts_a_timing() -> None:
    when = parse_when("todos los lunes a las 12", NOW, BUENOS_AIRES)

    assert when is not None and when.schedule.repeat is Repeat.WEEKLY
    assert parse_when("mañana, a las 9", NOW, BUENOS_AIRES) is not None
    assert parse_when("mañana a las 9 pagar la luz", NOW, BUENOS_AIRES) is None


def test_huge_messages_are_not_read() -> None:
    assert parse_reminder("recordame mañana " + "x " * 600, NOW, BUENOS_AIRES) is None


def test_is_reminder_request() -> None:
    assert is_reminder_request("Recordame mañana a las 9")
    assert is_reminder_request("che, avisame el lunes")
    assert not is_reminder_request("uber 2000")


def test_clean_text() -> None:
    assert clean_text("  que tengo que tomar la pastilla. ") == "tengo que tomar la pastilla"
    assert clean_text("de pagar la luz") == "pagar la luz"
