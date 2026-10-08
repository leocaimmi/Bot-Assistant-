"""Reads workout messages such as ``"pecho: banco plano 4x12 60kg, inclinado con mancuerna 3x8"``.

Format: optional day and muscle group, then exercises separated by commas, ``;``, ``y``
(``e`` before an i), or line breaks. Each exercise is ``<name> <sets>x<reps> [weight]``:
sets first, then reps. Also reads the new values of an exercise already logged
(``"3x10 40kg"``, ``"sin peso"``).
"""

import re
from dataclasses import dataclass, replace
from datetime import date

from asistente.core.dates import parse_day
from asistente.core.text import fold, normalize
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

# Sets x reps: "4x12", "4 x 12", "4 por 12" (also with the multiplication sign), or
# "4 series de 12".
_SETS_REPS = re.compile(r"(?P<sets>\d{1,2})\s*(?:[x\u00d7*]|por)\s*(?P<reps>\d{1,3})\b")
_SERIES = re.compile(
    r"(?P<sets>\d{1,2})\s*series?\s*(?:de|por|x)\s*(?P<reps>\d{1,3})"
    r"(?:\s*(?:reps?|repeticiones))?\b"
)
_WEIGHT_WITH_UNIT = re.compile(r"(?:\bcon\s+)?(?P<kg>\d{1,4}(?:[.,]\d{1,3})?)\s*(?:kgs?|kilos?)\b")
_BARE_WEIGHT_AFTER = re.compile(r"^\s*(?:con\s+)?(?P<kg>\d{1,4}(?:[.,]\d{1,3})?)\s*$")
_NO_WEIGHT = re.compile(r"\bsin\s+(?:peso|kilos?)\b")
# Exercise separators: line breaks, ";", " y " (" e " in "e inclinado"), and commas that
# are not decimal commas.
_SEPARATORS = re.compile(r"\s*(?:[;\n]|,(?!\d)|\s[ye]\s)\s*")


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


@dataclass(frozen=True, slots=True)
class SetChange:
    """New values of a logged exercise; ``None`` keeps the current one."""

    sets: int | None = None
    reps: int | None = None
    weight_grams: int | None = None
    no_weight: bool = False  # "sin peso": the weight is removed

    def applied_to(
        self, sets: int, reps: int, weight_grams: int | None
    ) -> tuple[int, int, int | None]:
        """``(sets, reps, weight_grams)`` once this change is made."""
        weight = None if self.no_weight else self.weight_grams or weight_grams
        return self.sets or sets, self.reps or reps, weight


def looks_like_workout(text: str) -> bool:
    """Cheap check: does the text mention sets x reps anywhere?"""
    lowered = text.casefold()
    return bool(_SETS_REPS.search(lowered) or _SERIES.search(lowered))


def parse_workout(text: str, today: date) -> ParsedWorkout | None:
    """Every exercise of the message, or ``None`` if any part does not follow the format."""
    text, day = take_day(text.casefold(), today)

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


def parse_set_change(text: str, *, bare_weight: bool = True) -> SetChange | None:
    """``"3x10 40kg"``, ``"3x10"``, ``"40kg"``, ``"sin peso"``; with ``bare_weight`` also
    ``"3x10 40"`` and ``"42,5"`` (kilos).

    ``None`` when nothing is said, a value is invalid, or anything else is said.
    """
    text = fold(text)
    try:
        change = find_set_change(text)
    except ValueError:
        return None
    rest = strip_set_values(text).strip(" .;:")
    has_weight = change is not None and (change.weight_grams or change.no_weight)
    if bare_weight and not has_weight and (bare := _BARE_WEIGHT_AFTER.match(rest)) is not None:
        # Here a lone number can only be the weight: "3x10 40", "42,5".
        weight_grams = parse_kg(bare["kg"])
        if weight_grams is None:
            return None
        change, rest = replace(change or SetChange(), weight_grams=weight_grams), ""
    if change is None or set(normalize(rest).split()) - {"con", "y", "de"}:
        return None
    return change


def find_set_change(text: str) -> SetChange | None:
    """New values said anywhere in ``text`` (casefolded); ``None`` if nothing is said.

    Bare numbers are not read (``"uber 2500"`` is not a weight). Raises ``ValueError``
    if a value is invalid or two values contradict each other.
    """
    sets_reps = [*_SETS_REPS.finditer(text), *_SERIES.finditer(text)]
    weights = list(_WEIGHT_WITH_UNIT.finditer(text))
    no_weight = _NO_WEIGHT.search(text) is not None
    if len(sets_reps) > 1 or len(weights) > 1 or (weights and no_weight):
        raise ValueError("contradicting values")
    if not (sets_reps or weights or no_weight):
        return None

    sets = reps = weight_grams = None
    if sets_reps:
        sets, reps = int(sets_reps[0]["sets"]), int(sets_reps[0]["reps"])
        if not (1 <= sets <= MAX_SETS and 1 <= reps <= MAX_REPS):
            raise ValueError("sets or reps out of range")
    if weights and (weight_grams := parse_kg(weights[0]["kg"])) is None:
        raise ValueError("invalid weight")
    return SetChange(sets, reps, weight_grams, no_weight=no_weight)


def strip_set_values(text: str) -> str:
    """``text`` (casefolded) without its sets x reps and weights."""
    for pattern in (_SETS_REPS, _SERIES, _WEIGHT_WITH_UNIT, _NO_WEIGHT):
        text = pattern.sub(" ", text)
    return text


def take_day(text: str, today: date) -> tuple[str, date | None]:
    """The first word that is a day (``"ayer"``, ``"miércoles"``) and the text without it."""
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
