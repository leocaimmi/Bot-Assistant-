"""Turns a free-text message such as ``"uber 2000 ayer"`` into its parts."""

from dataclasses import dataclass
from datetime import date

from asistente.core.dates import parse_day
from asistente.core.errors import UserError
from asistente.core.money import find_amounts
from asistente.finance.models import TransactionKind


class MissingAmountError(UserError):
    def __init__(self) -> None:
        super().__init__(
            "🤔 No encontré el importe. Escribilo así: <code>uber 2000</code>, "
            "<code>gym 47.000</code> o <code>transferencia utn 200.000</code>.\n"
            "Mirá /ayuda para más ejemplos."
        )


@dataclass(frozen=True, slots=True)
class ParsedEntry:
    amount_cents: int
    # Remaining words, in the user's original spelling (account and category come from here).
    words: tuple[str, ...]
    # Forced by a leading "+" (income) or "-" (expense); None means "decide by keywords".
    kind: TransactionKind | None
    # None means "now".
    day: date | None


def parse_entry(text: str, *, today: date) -> ParsedEntry:
    """Extract amount, optional sign and date. Raises ``MissingAmountError``.

    When several numbers appear ("3 cafés 6000"), the largest one is the amount: the
    others are usually quantities and stay in the description.
    """
    text = text.strip()
    kind: TransactionKind | None = None
    if text[:1] in ("+", "-"):
        kind = TransactionKind.INCOME if text[0] == "+" else TransactionKind.EXPENSE
        text = text[1:]

    tokens = text.split()
    amounts = find_amounts(tokens)
    if not amounts:
        raise MissingAmountError
    amount = max(reversed(amounts), key=lambda match: match.cents)
    used = set(range(amount.start, amount.end))

    day: date | None = None
    for index, token in enumerate(tokens):
        if index not in used and (parsed_day := parse_day(token, today)) is not None:
            day = parsed_day
            used.add(index)
            break

    words = tuple(
        token
        for index, token in enumerate(tokens)
        if index not in used and any(char.isalnum() for char in token)
    )
    return ParsedEntry(amount_cents=amount.cents, words=words, kind=kind, day=day)
