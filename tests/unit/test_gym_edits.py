from datetime import date

import pytest

from asistente.gym.edits import WorkoutEdit, parse_workout_edit
from asistente.gym.parser import SetChange

TODAY = date(2026, 10, 8)  # a Thursday
WEDNESDAY = date(2026, 10, 7)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Quiero cambiar algo del entrenamiento del miércoles",
            WorkoutEdit(exercise=(), day=WEDNESDAY, change=None),
        ),
        ("borrar el entreno de ayer", WorkoutEdit((), WEDNESDAY, None)),
        ("editar la rutina", WorkoutEdit((), None, None)),
        (
            "cambiar press militar a 40kg",
            WorkoutEdit(("press", "militar"), None, SetChange(weight_grams=40_000)),
        ),
        (
            "cambiar el press militar de 3x8 a 3x10",
            WorkoutEdit(("press", "militar"), None, SetChange(3, 10)),
        ),
        (
            "cambiar el peso del press a 42,5",
            WorkoutEdit(("press",), None, SetChange(weight_grams=42_500)),
        ),
        (
            "Al press militar del miércoles ponele 40 kilos",
            WorkoutEdit(("press", "militar"), WEDNESDAY, SetChange(weight_grams=40_000)),
        ),
        (
            "me olvidé de poner el peso de vuelos laterales: 7,5 kg",
            WorkoutEdit(("vuelos", "laterales"), None, SetChange(weight_grams=7_500)),
        ),
        (
            "el banco plano de ayer eran 4x10",
            WorkoutEdit(("banco", "plano"), WEDNESDAY, SetChange(4, 10)),
        ),
        (
            "corregir sentadilla sin peso",
            WorkoutEdit(("sentadilla",), None, SetChange(no_weight=True)),
        ),
        # Unclear values: the exercise is shown so the user writes them.
        ("el press eran 3x10 no 3x8", WorkoutEdit(("press",), None, None)),
    ],
)
def test_reads_workout_edits(text: str, expected: WorkoutEdit) -> None:
    assert parse_workout_edit(text, TODAY) == expected


@pytest.mark.parametrize(
    "text",
    [
        # Movements and new workouts are not workout edits.
        "cambiar uber 2000 a 2500",
        "cambiar uber a comida",
        "cambiar el uber a 500",
        "borrar el gym",
        "cambiar gym 47000 a 50000",
        "quiero editar algo",
        "pecho: banco plano 4x12 60kg",
        "en vez de pecho hice espalda: dominadas 4x8",
        "hice press militar 3x8 con 40 kilos, me olvidé de anotarlo",
        "uber 2000",
    ],
)
def test_ignores_everything_else(text: str) -> None:
    assert parse_workout_edit(text, TODAY) is None
