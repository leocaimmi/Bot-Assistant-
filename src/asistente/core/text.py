import re
import unicodedata

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def fold(text: str) -> str:
    """Lowercase without accents, keeping punctuation: ``'Millón'`` -> ``'millon'``."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize(text: str) -> str:
    """Comparable form of free text: ``'  Café-Martínez!'`` -> ``'cafe martinez'``."""
    return " ".join(_NON_ALPHANUMERIC.sub(" ", fold(text)).split())
