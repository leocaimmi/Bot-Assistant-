"""Argentine peso amounts: reading what the user types and formatting for display.

Amounts are handled as integer cents to avoid floating point rounding errors.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from asistente.core.text import fold

MAX_AMOUNT_CENTS = 10**14  # $1.000.000.000.000: anything above is surely a typo.

MULTIPLIERS: dict[str, int] = {
    "k": 1_000,
    "mil": 1_000,
    "luca": 1_000,
    "lucas": 1_000,
    "m": 1_000_000,
    "palo": 1_000_000,
    "palos": 1_000_000,
    "millon": 1_000_000,
    "millones": 1_000_000,
}

_AMOUNT_TOKEN = re.compile(r"\$?(?P<number>\d+(?:[.,]\d+)*)(?P<suffix>[a-z]+)?")
_EDGE_PUNCTUATION = ".,;:!?()"


@dataclass(frozen=True, slots=True)
class AmountMatch:
    """An amount found in a list of words: ``tokens[start:end]`` produced ``cents``."""

    start: int
    end: int
    cents: int


def find_amounts(tokens: Sequence[str]) -> list[AmountMatch]:
    """Every amount in ``tokens``, e.g. ``["uber", "2.500"]`` or ``["200", "mil"]``."""
    matches: list[AmountMatch] = []
    index = 0
    while index < len(tokens):
        match = _amount_at(tokens, index)
        if match is None:
            index += 1
        else:
            matches.append(match)
            index = match.end
    return matches


def parse_amount(text: str) -> int:
    """Strictly parse a text that only contains an amount. Raises ``ValueError``."""
    tokens = text.split()
    match = _amount_at(tokens, 0) if tokens else None
    if match is None or match.end != len(tokens):
        raise ValueError(f"not an amount: {text!r}")
    return match.cents


def format_ars(cents: int, *, signed: bool = False) -> str:
    """``150050`` -> ``'$1.500,50'``; ``200000`` -> ``'$2.000'`` (decimals only if needed)."""
    sign = "-" if cents < 0 else "+" if signed and cents > 0 else ""
    pesos, centavos = divmod(abs(cents), 100)
    integer_part = f"{pesos:,}".replace(",", ".")
    decimal_part = f",{centavos:02d}" if centavos else ""
    return f"{sign}${integer_part}{decimal_part}"


def _amount_at(tokens: Sequence[str], index: int) -> AmountMatch | None:
    token = fold(tokens[index]).strip(_EDGE_PUNCTUATION)
    parsed = _AMOUNT_TOKEN.fullmatch(token)
    if parsed is None:
        return None

    end = index + 1
    suffix = parsed["suffix"]
    if suffix is None and end < len(tokens):
        next_word = fold(tokens[end]).strip(_EDGE_PUNCTUATION)
        if next_word in MULTIPLIERS:
            suffix, end = next_word, end + 1
    if suffix is not None and suffix not in MULTIPLIERS:
        return None

    value = _parse_number(parsed["number"])
    if value is None:
        return None
    cents = value * MULTIPLIERS.get(suffix or "", 1) * 100
    if cents != cents.to_integral_value() or not 0 < cents <= MAX_AMOUNT_CENTS:
        return None
    return AmountMatch(start=index, end=end, cents=int(cents))


def _parse_number(raw: str) -> Decimal | None:
    """Read Argentine (``1.500,50``) and US (``1,500.50``) styles.

    With a single kind of separator, three digits after it mean thousands (``47.000``)
    and one or two mean decimals (``1,5``).
    """
    marks = [char for char in raw if char in ".,"]
    if not marks:
        return Decimal(raw)

    last = max(raw.rfind("."), raw.rfind(","))
    integer_part, decimals = raw[:last], raw[last + 1 :]

    if len(set(marks)) == 2:
        decimal_mark = raw[last]
        thousands_mark = "," if decimal_mark == "." else "."
        if marks.count(decimal_mark) != 1 or len(decimals) > 2:
            return None
        if not _is_grouped(integer_part, thousands_mark):
            return None
        return Decimal(f"{integer_part.replace(thousands_mark, '')}.{decimals}")

    mark = marks[0]
    if len(marks) == 1 and len(decimals) <= 2:
        return Decimal(f"{integer_part}.{decimals}")
    if _is_grouped(raw, mark):
        return Decimal(raw.replace(mark, ""))
    return None


def _is_grouped(raw: str, mark: str) -> bool:
    head, *groups = raw.split(mark)
    return 1 <= len(head) <= 3 and all(len(group) == 3 for group in groups)
