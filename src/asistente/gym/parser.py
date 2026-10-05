"""Reads workout messages such as ``"pecho: banco plano 4x12 60kg, inclinado con mancuerna 3x8"``.

Format: optional day and muscle group, then exercises separated by commas, ``;``, ``y`` or
line breaks. Each exercise is ``<name> <sets>x<reps> [weight]``: sets first, then reps.
"""

import re
from dataclasses import dataclass
from datetime import date

from asistente.core.dates import parse_day
from asistente.core.text import fold
from asistente.gym.models import MAX_EXERCISE_NAME_LENGTH, MuscleGroup
from asistente.gym.units import parse_kg

MAX_SETS = 20
MAX_REPS = 200

MUSCLE_WORDS: dict[str, MuscleGroup] = {
    "pecho": MuscleGroup.CHEST,
    "pectoral": MuscleGroup.CHEST,
    "pectorales": MuscleGroup.CHEST,
    "espalda": MuscleGroup.BACK,
    "dorsal": MuscleGroup.BACK,
    "dorsales": MuscleGroup.BACK,
    "pierna": MuscleGroup.LEGS,
    "piernas": MuscleGroup.LEGS,
    "cuadriceps": MuscleGroup.LEGS,
    "gluteos": MuscleGroup.LEGS,
    "gemelos": MuscleGroup.LEGS,
    "hombro": MuscleGroup.SHOULDERS,
    "hombros": MuscleGroup.SHOULDERS,
    "biceps": MuscleGroup.BICEPS,
    "bicep": MuscleGroup.BICEPS,
    "triceps": MuscleGroup.TRICEPS,
    "tricep": MuscleGroup.TRICEPS,
    "abdominales": MuscleGroup.ABS,
    "abdomen": MuscleGroup.ABS,
    "abs": MuscleGroup.ABS,
}
_LEAD_WORDS = {"hice", "hoy", "entrene", "entreno", "rutina", "dia", "de", ":"}

# Sets x reps: "4x12", "4 x 12" (x or the multiplication sign), or "4 series de 12".
_SETS_REPS = re.compile(r"(?P<sets>\d{1,2})\s*[x\u00d7*]\s*(?P<reps>\d{1,3})\b")
_SERIES = re.compile(
    r"(?P<sets>\d{1,2})\s*series?\s*(?:de|por|x)\s*(?P<reps>\d{1,3})"
    r"(?:\s*(?:reps?|repeticiones))?\b"
)
_WEIGHT_WITH_UNIT = re.compile(r"(?:\bcon\s+)?(?P<kg>\d{1,4}(?:[.,]\d{1,3})?)\s*(?:kgs?|kilos?)\b")
_BARE_WEIGHT_AFTER = re.compile(r"^\s*(?:con\s+)?(?P<kg>\d{1,4}(?:[.,]\d{1,3})?)\s*$")
# Exercise separators: line breaks, ";", " y ", and commas that are not decimal commas.
_SEPARATORS = re.compile(r"\s*(?:[;\n]|,(?!\d)|\sy\s)\s*")


@dataclass(frozen=True, slots=True)
class ExerciseItem:
    name: str
    # None when the message mentions several groups and it is unclear which one applies.
    muscle_group: MuscleGroup | None
    sets: int
    reps: int
    weight_grams: int | None


@dataclass(frozen=True, slots=True)
class ParsedWorkout:
    day: date | None
    items: tuple[ExerciseItem, ...]


def looks_like_workout(text: str) -> bool:
    """Cheap check: does the text mention sets x reps anywhere?"""
    lowered = text.casefold()
    return bool(_SETS_REPS.search(lowered) or _SERIES.search(lowered))


def parse_workout(text: str, today: date) -> ParsedWorkout | None:
    """Every exercise of the message, or ``None`` if any part does not follow the format."""
    text, day = _take_day(text.casefold(), today)

    items: list[ExerciseItem] = []
    groups: list[MuscleGroup] = []
    collecting_groups = True  # consecutive group-only parts add up: "pecho y triceps:"
    for segment in _SEPARATORS.split(text):
        words = segment.replace(":", " : ").split()
        lead: list[MuscleGroup] = []
        while words and (fold(words[0]) in MUSCLE_WORDS or fold(words[0]) in _LEAD_WORDS):
            word = fold(words.pop(0))
            if word in MUSCLE_WORDS:
                lead.append(MUSCLE_WORDS[word])
        if lead:
            groups = [*groups, *lead] if collecting_groups else lead
        if not words:
            collecting_groups = True
            continue

        item = _parse_exercise(" ".join(words), groups)
        if item is None:
            return None
        items.append(item)
        collecting_groups = False

    return ParsedWorkout(day=day, items=tuple(items)) if items else None


def _take_day(text: str, today: date) -> tuple[str, date | None]:
    tokens = text.split(" ")
    for index, token in enumerate(tokens):
        day = parse_day(token.strip(",;:."), today)
        if day is not None:
            return " ".join(tokens[:index] + tokens[index + 1 :]), day
    return text, None


def _parse_exercise(text: str, groups: list[MuscleGroup]) -> ExerciseItem | None:
    match = _SETS_REPS.search(text) or _SERIES.search(text)
    if match is None:
        return None
    sets, reps = int(match["sets"]), int(match["reps"])
    if not (1 <= sets <= MAX_SETS and 1 <= reps <= MAX_REPS):
        return None

    # Whatever is not sets x reps (nor weight) is the exercise name.
    name_part = f"{text[: match.start()]} {text[match.end() :]}"
    if _SETS_REPS.search(name_part) or _SERIES.search(name_part):
        return None  # two exercises with no separator: "banco 4x12 inclinado 3x8"
    weight_text: str | None = None
    if (weight := _WEIGHT_WITH_UNIT.search(name_part)) is not None:
        weight_text = weight["kg"]
        name_part = f"{name_part[: weight.start()]} {name_part[weight.end() :]}"
    elif (bare := _BARE_WEIGHT_AFTER.match(text[match.end() :])) is not None:
        # "4x12 60": a lone number right after the reps is the weight in kg.
        weight_text = bare["kg"]
        name_part = text[: match.start()]
    weight_grams = parse_kg(weight_text) if weight_text is not None else None
    if weight_text is not None and weight_grams is None:
        return None

    name = " ".join(name_part.replace(":", " ").split()).strip(" ,.-")
    name = re.sub(r"\s+con$", "", name)
    if not name or len(name) > MAX_EXERCISE_NAME_LENGTH:
        return None
    group = groups[0] if len(set(groups)) == 1 else None
    return ExerciseItem(
        name=name[0].upper() + name[1:],
        muscle_group=group,
        sets=sets,
        reps=reps,
        weight_grams=weight_grams,
    )
