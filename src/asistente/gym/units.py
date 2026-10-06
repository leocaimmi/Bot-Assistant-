"""Weights: read what the user types and format it back, stored as integer grams."""

from decimal import Decimal, InvalidOperation

MAX_WEIGHT_GRAMS = 1_000_000  # 1000 kg: anything above is a typo


def parse_kg(text: str) -> int | None:
    """``"62,5"`` or ``"62.5"`` kilos -> ``62500`` grams. ``None`` if not a valid weight."""
    try:
        kilos = Decimal(text.strip().replace(",", "."))
    except InvalidOperation:
        return None
    grams = kilos * 1000
    if grams != grams.to_integral_value() or not 0 < grams <= MAX_WEIGHT_GRAMS:
        return None
    return int(grams)


def format_kg(grams: int) -> str:
    """``62500`` -> ``"62,5 kg"``; ``60000`` -> ``"60 kg"``."""
    kilos = Decimal(grams) / 1000
    text = f"{kilos.normalize():f}".replace(".", ",")
    return f"{text} kg"
