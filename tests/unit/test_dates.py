from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from asistente.core.dates import (
    at_local_time,
    format_datetime,
    month_label,
    month_range,
    parse_day,
    parse_month,
    shift_month,
)

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")
TODAY = date(2026, 10, 5)


def test_month_range_uses_local_midnight() -> None:
    start, end = month_range(2026, 10, BUENOS_AIRES)

    assert start == datetime(2026, 10, 1, 3, 0, tzinfo=UTC)
    assert end == datetime(2026, 11, 1, 3, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("year", "month", "delta", "expected"),
    [(2026, 10, 1, (2026, 11)), (2026, 12, 1, (2027, 1)), (2026, 1, -1, (2025, 12))],
)
def test_shift_month(year: int, month: int, delta: int, expected: tuple[int, int]) -> None:
    assert shift_month(year, month, delta) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("septiembre", (2026, 9)),
        ("Octubre", (2026, 10)),
        ("diciembre", (2025, 12)),
        ("sep", (2026, 9)),
        ("setiembre", (2026, 9)),
        ("marzo 2025", (2025, 3)),
        ("9", (2026, 9)),
        ("11", (2025, 11)),
        ("09/2026", (2026, 9)),
        ("9/26", (2026, 9)),
        ("2026-09", (2026, 9)),
    ],
)
def test_parse_month(text: str, expected: tuple[int, int]) -> None:
    assert parse_month(text, TODAY) == expected


@pytest.mark.parametrize("text", ["", "marzoo", "13", "0", "13/2026", "marzo 1999", "1 2 3"])
def test_parse_month_rejects_invalid_input(text: str) -> None:
    assert parse_month(text, TODAY) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hoy", date(2026, 10, 5)),
        ("Ayer", date(2026, 10, 4)),
        ("anteayer", date(2026, 10, 3)),
        ("15/09", date(2026, 9, 15)),
        ("20/12", date(2025, 12, 20)),
        ("15/09/2025", date(2025, 9, 15)),
        ("1/2/26", date(2026, 2, 1)),
        # TODAY is a Monday: a weekday is the latest one, today included.
        ("lunes", date(2026, 10, 5)),
        ("domingo", date(2026, 10, 4)),
        ("el miércoles", date(2026, 9, 30)),
        ("Sábado", date(2026, 10, 3)),
    ],
)
def test_parse_day(text: str, expected: date) -> None:
    assert parse_day(text, TODAY) == expected


@pytest.mark.parametrize(
    "text", ["mañana", "32/01", "15/13", "29/02/2026", "2000", "15-09", "sabados", "el"]
)
def test_parse_day_rejects_invalid_input(text: str) -> None:
    assert parse_day(text, TODAY) is None


def test_formatting_in_local_time() -> None:
    moment = datetime(2026, 10, 5, 17, 32, tzinfo=UTC)

    assert format_datetime(moment, BUENOS_AIRES) == "05/10/2026 14:32"
    assert month_label(2026, 10) == "octubre 2026"


def test_at_local_time_is_aware() -> None:
    moment = at_local_time(date(2026, 10, 4), time(14, 30), BUENOS_AIRES)

    assert moment.astimezone(UTC) == datetime(2026, 10, 4, 17, 30, tzinfo=UTC)
