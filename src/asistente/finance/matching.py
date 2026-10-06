"""Find known phrases (category keywords, account aliases) inside the words of a message."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from asistente.core.text import normalize

MAX_PHRASE_TOKENS = 3

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PhraseMatch(Generic[T]):
    """``tokens[start:end]`` matched a phrase that maps to ``value``."""

    value: T
    start: int
    end: int


def find_phrase(tokens: Sequence[str], phrases: Mapping[str, T]) -> PhraseMatch[T] | None:
    """The best phrase in ``tokens``: longer phrases first, then the earliest one.

    ``phrases`` keys must be normalized (see ``core.text.normalize``). Tokens are compared
    in normalized form, so ``"Pedidos Ya"`` and ``"pedidos-ya"`` both match ``"pedidos ya"``.
    """
    for size in range(min(MAX_PHRASE_TOKENS, len(tokens)), 0, -1):
        for start in range(len(tokens) - size + 1):
            candidate = normalize(" ".join(tokens[start : start + size]))
            if candidate in phrases:
                return PhraseMatch(phrases[candidate], start, start + size)
    return None
