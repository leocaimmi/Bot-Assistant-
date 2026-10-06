"""Text commands on existing transactions: ``borrar uber 2000``, ``cambiar uber 2000 a 2500``.

Pure parsing only: the service finds the transaction and applies the change.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from asistente.core.dates import parse_day
from asistente.core.money import find_amounts
from asistente.core.text import normalize


class CommandKind(StrEnum):
    DELETE = "delete"
    EDIT = "edit"


# Normalized (no accents), so "borrá" and "cambiá" match too. Ambiguous words such as
# "sacar" ("sacar plata 5000" is an expense) are deliberately left out.
_VERBS = {
    "borrar": CommandKind.DELETE,
    "borra": CommandKind.DELETE,
    "eliminar": CommandKind.DELETE,
    "elimina": CommandKind.DELETE,
    "anular": CommandKind.DELETE,
    "anula": CommandKind.DELETE,
    "cambiar": CommandKind.EDIT,
    "cambia": CommandKind.EDIT,
    "editar": CommandKind.EDIT,
    "edita": CommandKind.EDIT,
    "corregir": CommandKind.EDIT,
    "corregi": CommandKind.EDIT,
    "corrige": CommandKind.EDIT,
    "modificar": CommandKind.EDIT,
    "modifica": CommandKind.EDIT,
}
_STOP_WORDS = {"el", "la", "los", "las", "un", "una", "de", "del", "al", "mi", "movimiento"}
_LATEST_WORDS = {"ultimo", "ultima"}
# "el uber eran 2500", "en vez de 2000": corrections, never a new movement.
_CORRECTION_WORDS = {"era", "eran", "vez", "lugar", "equivoque", "equivocado", "equivocada"}


# Longer commands ("modificar la última transferencia y poner...") are left to the AI.
MAX_SIMPLE_COMMAND_TOKENS = 8


@dataclass(frozen=True, slots=True)
class TextCommand:
    kind: CommandKind
    rest: str  # everything after the verb: "uber 2000 a 2500"


@dataclass(frozen=True, slots=True)
class TargetQuery:
    """What identifies an existing transaction."""

    words: tuple[str, ...]  # normalized, e.g. ("uber",)
    amount_cents: int | None
    day: date | None
    latest: bool  # "el último": the most recent one

    @property
    def is_empty(self) -> bool:
        return not (self.words or self.amount_cents or self.day or self.latest)


def parse_command(text: str) -> TextCommand | None:
    # Any whitespace ends the verb: a dictated "Borrar. El uber" arrives as two lines.
    first, _, rest = " ".join(text.split()).partition(" ")
    kind = _VERBS.get(normalize(first))
    return TextCommand(kind=kind, rest=rest.strip()) if kind is not None else None


def is_simple_command(text: str) -> bool:
    """Short enough for the rules: ``cambiar uber 2000 a 2500``, ``borrar el último``."""
    return len(text.split()) <= MAX_SIMPLE_COMMAND_TOKENS


def looks_like_correction(text: str) -> bool:
    """A correction ("eran 2500") or a command verb anywhere ("perdón, modificar...")."""
    return any(word in _CORRECTION_WORDS or word in _VERBS for word in normalize(text).split())


def split_new_value(rest: str) -> tuple[str, str] | None:
    """``"uber 2000 a 2500"`` -> ``("uber 2000", "2500")``; ``None`` without `` a ``."""
    target, separator, new_value = rest.rpartition(" a ")
    if not separator or not target.strip() or not new_value.strip():
        return None
    return target.strip(), new_value.strip()


def parse_target(text: str, today: date) -> TargetQuery:
    tokens = text.split()
    amounts = find_amounts(tokens)
    used = {index for match in amounts for index in range(match.start, match.end)}
    amount_cents = max((match.cents for match in amounts), default=None)

    day: date | None = None
    for index, token in enumerate(tokens):
        if index not in used and (parsed := parse_day(token, today)) is not None:
            day = parsed
            used.add(index)
            break

    words = [
        word
        for index, token in enumerate(tokens)
        if index not in used
        for word in normalize(token).split()
    ]
    latest = any(word in _LATEST_WORDS for word in words)
    meaningful = tuple(w for w in words if w not in _STOP_WORDS and w not in _LATEST_WORDS)
    return TargetQuery(words=meaningful, amount_cents=amount_cents, day=day, latest=latest)
