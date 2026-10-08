"""Requests to fix a logged workout, typed or dictated.

``"cambiar press militar a 40kg"``, ``"al press militar del miércoles ponele 40 kilos"``,
``"quiero cambiar algo del entrenamiento del miércoles"``. Pure parsing only: the service
finds the exercise and the bot shows the change before making it.
"""

from dataclasses import dataclass
from datetime import date

from asistente.core.commands import CORRECTION_WORDS, VERBS
from asistente.core.text import fold, normalize
from asistente.gym.parser import (
    SetChange,
    find_set_change,
    parse_set_change,
    strip_set_values,
    take_day,
)

# Words that make a request about workouts. "gym" is not one: "borrar el gym" is the fee.
_GYM_WORDS = frozenset(
    {
        "entrenamiento",
        "entrenamientos",
        "entreno",
        "entrenos",
        "rutina",
        "ejercicio",
        "ejercicios",
        "serie",
        "series",
        "repeticiones",
        "reps",
        "peso",
    }
)
# Besides the shared verbs: "ponele 40 kilos", "me olvidé el peso", "eran 3x10". "en vez
# de" is left out: "en vez de pecho hice espalda: dominadas 4x8" is a new workout.
_FIX_WORDS = (
    frozenset(VERBS)
    | (CORRECTION_WORDS - {"vez", "lugar"})
    | {"ponele", "ponerle", "pone", "poner", "agregale", "agregarle", "sumale", "olvide"}
    | {"falto", "faltaba"}
)
# "me olvidé de anotarlo": something new to log, not a fix.
_NEW_LOG_WORDS = frozenset({"anotar", "anotarlo", "anota", "anotalo", "cargar", "cargarlo"})
# Words that never name an exercise.
_FILLER = frozenset(
    {
        "quiero",
        "queria",
        "quisiera",
        "necesito",
        "algo",
        "el",
        "la",
        "los",
        "las",
        "lo",
        "un",
        "una",
        "de",
        "del",
        "al",
        "a",
        "en",
        "que",
        "me",
        "se",
        "le",
        "mi",
        "por",
        "favor",
        "porfa",
        "y",
        "con",
        "no",
        "hice",
        "puse",
        "dia",
        "ultimo",
        "ultima",
        "kilos",
        "kilo",
        "kg",
        "gym",
        "gimnasio",
    }
)
_NOT_THE_EXERCISE = _GYM_WORDS | _FIX_WORDS | _FILLER


@dataclass(frozen=True, slots=True)
class WorkoutEdit:
    exercise: tuple[str, ...]  # normalized words that name it; empty if not said
    day: date | None
    change: SetChange | None  # None: show it, so the user picks what to change


def parse_workout_edit(text: str, today: date) -> WorkoutEdit | None:
    """What to fix in a logged workout; ``None`` if the text does not ask for that."""
    folded = " ".join(fold(text).split())
    target, change = _split_change(folded)
    target, day = take_day(target, today)
    words = normalize(target).split()
    if not any(word in _FIX_WORDS for word in words) or any(
        word in _NEW_LOG_WORDS for word in words
    ):
        return None
    if change is None:
        if any(word.isdigit() for word in words):
            return None  # "cambiar gym 47000": a number that is neither sets nor weight
        # Sets or a weight, even unclear ones ("eran 3x10 no 3x8"), are about the gym.
        said_values = strip_set_values(folded) != folded
        if not said_values and not any(word in _GYM_WORDS for word in words):
            return None
    exercise = tuple(word for word in words if word not in _NOT_THE_EXERCISE)
    return WorkoutEdit(exercise=exercise, day=day, change=change)


def _split_change(text: str) -> tuple[str, SetChange | None]:
    """``"press de 3x8 a 3x10"`` -> ``("press de", 3x10)``; else values said anywhere."""
    target, separator, new_values = text.rpartition(" a ")
    if separator:
        # "cambiar el peso del press a 40": a lone number is the weight only when the
        # words already say this is about the gym.
        bare_weight = any(word in _GYM_WORDS for word in normalize(target).split())
        if (change := parse_set_change(new_values, bare_weight=bare_weight)) is not None:
            return strip_set_values(target), change
    try:
        change = find_set_change(text)
    except ValueError:
        change = None  # unclear values: the user picks the exercise and writes them
    return strip_set_values(text), change
