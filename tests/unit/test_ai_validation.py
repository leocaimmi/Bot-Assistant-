from datetime import date, datetime

import pytest

from asistente.ai import validation
from asistente.ai.schema import ExerciseDone, ReminderRequest
from asistente.core.schedule import Repeat
from asistente.finance.models import TransactionKind
from asistente.gym.models import MuscleGroup
from tests.ai_factories import exercise, movement, target
from tests.factories import BUENOS_AIRES

TODAY = date(2026, 10, 5)


@pytest.mark.parametrize(
    ("amount", "message", "cents"),
    [
        ("2000", "uber 2000", 200_000),
        ("2.000", "uber 2 lucas... digo 2000", 200_000),
        ("2000", "gasté dos lucas en el super", 200_000),  # no digits to compare with
        ("3000", "uber 2000", None),  # the AI changed the number
        ("abc", "uber 2000", None),
        (None, "uber 2000", None),
        ("0", "gasté cero", None),
    ],
)
def test_safe_amount(amount: str | None, message: str, cents: int | None) -> None:
    assert validation.safe_amount(amount, message) == cents


def test_to_entry() -> None:
    entry = validation.to_entry(
        movement("venta bici", "50.000", income=True, day="ayer", account="efectivo"),
        "vendí la bici en 50.000 ayer, en efectivo",
        TODAY,
    )

    assert entry is not None
    assert entry.amount_cents == 5_000_000
    assert entry.words == ("venta", "bici", "efectivo")
    assert entry.kind is TransactionKind.INCOME
    assert entry.day == date(2026, 10, 4)


def test_the_ai_says_which_way_the_money_went() -> None:
    entry = validation.to_entry(
        movement("transferencia a juan", "5000"), "le hice una transferencia a juan de 5000", TODAY
    )

    assert entry is not None
    assert entry.kind is TransactionKind.EXPENSE


@pytest.mark.parametrize(
    ("text", "expected"),
    [("10:00", (10, 0)), ("9:30", (9, 30)), ("24:00", None), ("10", None), (None, None)],
)
def test_safe_time(text: str | None, expected: tuple[int, int] | None) -> None:
    parsed = validation.safe_time(text)

    assert ((parsed.hour, parsed.minute) if parsed else None) == expected


def test_to_entry_rejects_invented_amount() -> None:
    assert validation.to_entry(movement("uber", "9999"), "uber 2000", TODAY) is None


def test_to_target() -> None:
    query = validation.to_target(
        target("el uber", "2000", "ayer"), "el uber de 2000 de ayer", TODAY
    )

    assert (query.words, query.amount_cents, query.day) == (("uber",), 200_000, date(2026, 10, 4))
    assert validation.to_target(None, "x", TODAY).is_empty
    assert validation.to_target(target(latest=True), "modificalo", TODAY).latest


def test_to_exercise_items() -> None:
    items = validation.to_exercise_items(
        [
            exercise("press plano", 4, 12, kg=62.5),
            exercise("fondos", 3, 10, group=MuscleGroup.TRICEPS),
        ],
        "press plano 4x12 con 62,5 y fondos 3x10",
    )

    assert items is not None
    assert [(i.name, i.muscle_group, i.sets, i.reps, i.weight_grams) for i in items] == [
        ("Press plano", MuscleGroup.CHEST, 4, 12, 62_500),
        ("Fondos", MuscleGroup.TRICEPS, 3, 10, None),
    ]


@pytest.mark.parametrize(
    ("done", "message"),
    [
        (exercise("press", 4, 12), "press 3x10"),  # numbers not in the message
        (exercise("press", 99, 12), "press 99x12"),  # too many sets
        (exercise("", 4, 12), "4x12"),
        (exercise("press", 4, 12, kg=5000), "press 4x12 5000"),
    ],
)
def test_to_exercise_items_rejects_bad_values(done: ExerciseDone, message: str) -> None:
    assert validation.to_exercise_items([done], message) is None


def test_spelled_out_workout_has_no_numbers_to_check() -> None:
    items = validation.to_exercise_items([exercise("press", 4, 12)], "press cuatro de doce")

    assert items is not None


def test_to_reminder_checks_the_timing_with_the_parser() -> None:
    now = datetime(2026, 10, 5, 10, 0, tzinfo=BUENOS_AIRES)

    def check(text: str, when: str) -> object:
        return validation.to_reminder(ReminderRequest(text=text, when=when), now, BUENOS_AIRES)

    parsed = check("la pastilla", "todos los lunes a las 12")
    assert parsed is not None
    assert parsed.schedule.repeat is Repeat.WEEKLY  # type: ignore[attr-defined]
    assert check("algo", "cuando pueda") is None
    assert check("algo", "mañana a las 9 y algo más") is None
    assert check("  ", "mañana") is None
    assert validation.to_reminder(None, now, BUENOS_AIRES) is None
