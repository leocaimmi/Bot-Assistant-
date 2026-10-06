"""OpenAI list prices, to know what each AI request costs (shown by /ia).

Costs are integers in micro-dollars (millionths of a US dollar): a request to a small model
costs a few hundred, and integer sums never drift. Tokens times the price per million tokens
is already in micro-dollars.

Prices from https://developers.openai.com/api/docs/pricing (checked on 2026-10-05).
"""

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import TypeVar

PriceT = TypeVar("PriceT")

_SNAPSHOT_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True, slots=True)
class TokenPrices:
    """US dollars per million tokens."""

    input: Decimal
    cached_input: Decimal
    # Writing a prompt prefix to the cache: GPT-5.6 and later bill it at 1.25x the input.
    cache_write: Decimal
    output: Decimal


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Tokens of one response. ``input_tokens`` includes the cached and cache-write ones."""

    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    cache_write_tokens: int = 0


TOKEN_PRICES: dict[str, TokenPrices] = {
    "gpt-6-luna": TokenPrices(
        input=Decimal("0.10"),
        cached_input=Decimal("0.01"),
        cache_write=Decimal("0.125"),
        output=Decimal("0.50"),
    ),
    # Before GPT-5.6, cache writes cost the same as plain input.
    "gpt-5.4-nano": TokenPrices(
        input=Decimal("0.20"),
        cached_input=Decimal("0.02"),
        cache_write=Decimal("0.20"),
        output=Decimal("1.25"),
    ),
}

# US dollars per minute of audio (OpenAI's estimate for the models billed by token).
TRANSCRIPTION_PRICES: dict[str, Decimal] = {
    "gpt-4o-mini-transcribe": Decimal("0.003"),
    "gpt-transcribe": Decimal("0.0045"),
    "gpt-4o-transcribe": Decimal("0.006"),
    "whisper-1": Decimal("0.006"),
}


def response_cost(model: str, usage: TokenUsage) -> int | None:
    """Micro-dollars for one response (rounded up), ``None`` if the price is unknown."""
    prices = _price_of(TOKEN_PRICES, model)
    if prices is None:
        return None
    uncached = max(usage.input_tokens - usage.cached_tokens - usage.cache_write_tokens, 0)
    cost = (
        uncached * prices.input
        + usage.cached_tokens * prices.cached_input
        + usage.cache_write_tokens * prices.cache_write
        + usage.output_tokens * prices.output
    )
    return math.ceil(cost)


def transcription_cost(model: str, seconds: int) -> int | None:
    """Micro-dollars for ``seconds`` of audio (rounded up), ``None`` if the price is unknown."""
    per_minute = _price_of(TRANSCRIPTION_PRICES, model)
    if per_minute is None:
        return None
    return math.ceil(per_minute * seconds * 1_000_000 / 60)


def has_price(model: str) -> bool:
    return (
        _price_of(TOKEN_PRICES, model) is not None
        or _price_of(TRANSCRIPTION_PRICES, model) is not None
    )


def _price_of(prices: Mapping[str, PriceT], model: str) -> PriceT | None:
    """Price of ``model``, or of its base model for a dated snapshot ("gpt-6-luna-2026-09-22").

    Other suffixes are different models ("gpt-6-luna-pro") and have no price here.
    """
    return prices.get(_SNAPSHOT_SUFFIX.sub("", model))
