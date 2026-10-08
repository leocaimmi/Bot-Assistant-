"""Words that ask to fix something already registered, shared by every module.

Pure vocabulary: each module decides what the fix applies to (a movement, an exercise).
"""

from enum import StrEnum

from asistente.core.text import normalize


class CommandKind(StrEnum):
    DELETE = "delete"
    EDIT = "edit"


# Normalized (no accents), so "borrá" and "cambiá" match too. Ambiguous words such as
# "sacar" ("sacar plata 5000" is an expense) are deliberately left out.
VERBS: dict[str, CommandKind] = {
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
# "el uber eran 2500", "en vez de 2000": corrections, never something new.
CORRECTION_WORDS = frozenset(
    {"era", "eran", "vez", "lugar", "equivoque", "equivocado", "equivocada"}
)
# Words that do not say what to fix: "quiero editar algo", "corregir lo último".
_VAGUE_WORDS = frozenset(
    {
        "quiero",
        "queria",
        "quisiera",
        "necesito",
        "como",
        "hago",
        "para",
        "puedo",
        "algo",
        "eso",
        "esto",
        "lo",
        "el",
        "la",
        "un",
        "una",
        "de",
        "del",
        "me",
        "que",
        "ultimo",
        "ultima",
        "anterior",
        "recien",
        "hice",
        "anote",
        "puse",
        "cargue",
        "dato",
        "cosa",
        "por",
        "favor",
        "porfa",
    }
)


def command_kind(word: str) -> CommandKind | None:
    """``"Borrá"`` -> ``DELETE``; ``None`` if the word is not a command verb."""
    return VERBS.get(normalize(word))


def looks_like_correction(text: str) -> bool:
    """A correction ("eran 2500") or a command verb anywhere ("perdón, modificar...")."""
    return any(word in CORRECTION_WORDS or word in VERBS for word in normalize(text).split())


def is_vague_edit(text: str) -> bool:
    """An edit that does not say what to fix: "quiero editar algo", "me equivoqué"."""
    words = normalize(text).split()
    asks = any(VERBS.get(word) is CommandKind.EDIT or word in CORRECTION_WORDS for word in words)
    return asks and all(
        word in VERBS or word in CORRECTION_WORDS or word in _VAGUE_WORDS for word in words
    )
