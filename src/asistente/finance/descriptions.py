"""Descriptions of movements: one or more items, each with a capital first letter.

``"una coca, Doritos picantes y un chocolate"`` -> ``"Coca, Doritos picantes, Chocolate"``.
Items are stored comma-separated, so searching and the monthly summary keep working with
plain text; the movement card lists them one per line.
"""

import re

ITEM_SEPARATOR = ", "

# Commas, semicolons and "+" separate items; a comma between digits ("3,5kg") does not.
_BREAKS = re.compile(r"\s*(?:;|\+|,(?!\d)|(?<!\d),)\s*")
# In a list ("coca, doritos y chocolate") the "y" separates items too, while a single
# "pan y queso" stays one item.
_AND = re.compile(r"\s+[ye]\s+", re.IGNORECASE)
# Articles at the start of an item say nothing: "una coca" is "Coca".
_ARTICLES = frozenset({"un", "una", "unos", "unas", "el", "la", "los", "las"})
_EDGE_PUNCTUATION = ".,;:!?¡¿()\"'«»-"


def format_description(text: str) -> str:
    """The items of ``text``, each capitalized, joined by ``ITEM_SEPARATOR``."""
    parts = [part for part in _BREAKS.split(text) if part.strip()]
    if len(parts) > 1:
        parts = [piece for part in parts for piece in _AND.split(part)]
    items = (_format_item(part) for part in parts)
    return ITEM_SEPARATOR.join(item for item in items if item)


def description_items(description: str) -> list[str]:
    """The items of a stored description: ``"Coca, Chocolate"`` -> ``["Coca", "Chocolate"]``."""
    return [item.strip() for item in description.split(ITEM_SEPARATOR) if item.strip()]


def _format_item(text: str) -> str:
    """``"una coca Doritos"`` -> ``"Coca doritos"``; acronyms (``YPF``) keep their capitals."""
    words = text.strip(_EDGE_PUNCTUATION + " ").split()
    while len(words) > 1 and words[0].casefold() in _ARTICLES:
        words.pop(0)
    if not words:
        return ""
    words = [word if _is_acronym(word) else word.lower() for word in words]
    words[0] = words[0][:1].upper() + words[0][1:]
    return " ".join(words)


def _is_acronym(word: str) -> bool:
    letters = [char for char in word if char.isalpha()]
    return 2 <= len(letters) <= 5 and all(char.isupper() for char in letters)
