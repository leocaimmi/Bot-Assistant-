from datetime import date

import pytest

from asistente.gym.models import MuscleGroup
from asistente.gym.parser import ExerciseItem, looks_like_workout, parse_workout

TODAY = date(2026, 10, 5)
CHEST = MuscleGroup.CHEST


def _items(text: str) -> tuple[ExerciseItem, ...]:
    parsed = parse_workout(text, TODAY)
    assert parsed is not None, text
    return parsed.items


def test_users_example() -> None:
    items = _items("pecho: banco plano 4x12 60kg, inclinado con mancuerna 3x8")

    assert items == (
        ExerciseItem("Banco plano", CHEST, sets=4, reps=12, weight_grams=60_000),
        ExerciseItem("Inclinado con mancuerna", CHEST, sets=3, reps=8, weight_grams=None),
    )


@pytest.mark.parametrize(
    "text",
    [
        "hice pecho banco plano 4 series de 12",
        "hice pecho banco plano 4 series por 12 reps",
        "Pecho: Banco plano 4 x 12",
        "pecho banco plano 4\u00d712",
    ],
)
def test_sets_and_reps_variants(text: str) -> None:
    (item,) = _items(text)

    assert (item.name, item.muscle_group, item.sets, item.reps) == ("Banco plano", CHEST, 4, 12)


@pytest.mark.parametrize(
    ("text", "grams"),
    [
        ("pecho banco plano 4x12 62,5kg", 62_500),
        ("pecho banco plano 4x12 62.5 kilos", 62_500),
        ("pecho banco plano 60kg 4x12", 60_000),
        ("pecho banco plano 4x12 con 60", 60_000),
        ("pecho banco plano 4x12 60", 60_000),
    ],
)
def test_weight_variants(text: str, grams: int) -> None:
    (item,) = _items(text)

    assert (item.name, item.weight_grams) == ("Banco plano", grams)


def test_several_groups_and_lines() -> None:
    items = _items(
        "piernas: sentadilla 4x10 80kg; prensa 3x12 120kg\nhombros\npress militar 4x8 40kg"
    )

    assert [(i.name, i.muscle_group) for i in items] == [
        ("Sentadilla", MuscleGroup.LEGS),
        ("Prensa", MuscleGroup.LEGS),
        ("Press militar", MuscleGroup.SHOULDERS),
    ]


def test_ambiguous_group_is_left_open() -> None:
    items = _items("hice pecho y triceps: banco plano 4x12, fondos 3x10")

    assert [(i.name, i.muscle_group) for i in items] == [
        ("Banco plano", None),
        ("Fondos", None),
    ]


def test_without_group_and_with_accents() -> None:
    (item,) = _items("jalón al pecho 4x10 50kg")

    assert (item.name, item.muscle_group) == ("Jalón al pecho", None)


def test_reads_the_day() -> None:
    parsed = parse_workout("ayer espalda: dominadas 4x8", TODAY)

    assert parsed is not None
    assert parsed.day == date(2026, 10, 4)
    assert parsed.items[0].name == "Dominadas"


@pytest.mark.parametrize(
    "text",
    [
        "uber 2000",
        "pecho: banco plano",
        "pecho: 4x12",
        "monitor 24x7 15000",
        "pecho: banco plano 4x12, algo raro",
        "pecho: banco plano 4x12 99999kg",
    ],
)
def test_rejects_what_does_not_follow_the_format(text: str) -> None:
    assert parse_workout(text, TODAY) is None


def test_looks_like_workout() -> None:
    assert looks_like_workout("banco plano 4x12 60")
    assert looks_like_workout("4 series de 12")
    assert not looks_like_workout("uber 2000")
