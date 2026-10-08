from datetime import date

import pytest

from asistente.gym.models import MuscleGroup
from asistente.gym.parser import (
    ExerciseItem,
    SetChange,
    find_set_change,
    looks_like_workout,
    parse_set_change,
    parse_workout,
    strip_set_values,
    take_day,
)

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
        "pecho banco plano 4 por 12",
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
        "pecho: banco plano 4x12 inclinado 3x8",
    ],
)
def test_rejects_what_does_not_follow_the_format(text: str) -> None:
    assert parse_workout(text, TODAY) is None


def test_spoken_style() -> None:
    items = _items("Hoy hice pecho: banco plano 4 por 12 con 60 kilos e inclinado 3 por 8")

    assert items == (
        ExerciseItem("Banco plano", CHEST, sets=4, reps=12, weight_grams=60_000),
        ExerciseItem("Inclinado", CHEST, sets=3, reps=8, weight_grams=None),
    )


def test_looks_like_workout() -> None:
    assert looks_like_workout("banco plano 4x12 60")
    assert looks_like_workout("4 series de 12")
    assert not looks_like_workout("uber 2000")


@pytest.mark.parametrize(
    ("text", "change"),
    [
        ("3x10 40kg", SetChange(3, 10, 40_000)),
        ("3 series de 10 con 40 kilos", SetChange(3, 10, 40_000)),
        ("3x10", SetChange(3, 10)),
        ("7,5 kg", SetChange(weight_grams=7_500)),
        ("3x10 40", SetChange(3, 10, 40_000)),
        ("42,5", SetChange(weight_grams=42_500)),
        ("sin peso", SetChange(no_weight=True)),
        ("3x10 sin peso", SetChange(3, 10, no_weight=True)),
    ],
)
def test_parse_set_change(text: str, change: SetChange) -> None:
    assert parse_set_change(text) == change


@pytest.mark.parametrize(
    "text", ["", "hola", "press 3x10", "3x500", "3x10 4x8", "40kg sin peso", "0", "3x10 0"]
)
def test_parse_set_change_rejects_anything_else(text: str) -> None:
    assert parse_set_change(text) is None


def test_bare_weights_can_be_turned_off() -> None:
    assert parse_set_change("2500", bare_weight=False) is None
    assert parse_set_change("3x10 40", bare_weight=False) is None
    assert parse_set_change("40kg", bare_weight=False) == SetChange(weight_grams=40_000)


def test_find_set_change_anywhere() -> None:
    assert find_set_change("ponele 40 kilos al press") == SetChange(weight_grams=40_000)
    assert find_set_change("el press eran 3x10") == SetChange(3, 10)
    assert find_set_change("cambiar uber a 2500") is None
    with pytest.raises(ValueError, match="contradicting"):
        find_set_change("eran 3x10 no 3x8")
    with pytest.raises(ValueError, match="out of range"):
        find_set_change("eran 30x10")


def test_strip_set_values() -> None:
    assert strip_set_values("press de 3x8 a 3x10 con 40kg sin peso").split() == [
        "press",
        "de",
        "a",
    ]


def test_set_change_keeps_what_is_not_said() -> None:
    assert SetChange(weight_grams=7_500).applied_to(3, 10, None) == (3, 10, 7_500)
    assert SetChange(4, 8).applied_to(3, 10, 40_000) == (4, 8, 40_000)
    assert SetChange(no_weight=True).applied_to(3, 10, 40_000) == (3, 10, None)


def test_take_day() -> None:
    assert take_day("press del miércoles", TODAY) == ("press del", date(2026, 9, 30))
    assert take_day("press militar", TODAY) == ("press militar", None)
