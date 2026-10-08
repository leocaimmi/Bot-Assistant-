"""Turns a free-text message such as ``"uber 2000 ayer"`` into its parts."""

from dataclasses import dataclass
from datetime import date

from asistente.core.dates import parse_day
from asistente.core.errors import UserError
from asistente.core.money import find_amounts
from asistente.core.text import fold, normalize
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


MAX_SIMPLE_ENTRY_TOKENS = 7

# Punctuation around a word ("uber," or "(efectivo)") is not part of the description.
_EDGE_PUNCTUATION = ".,;:!?¡¿()\"'«»"
# Marks that separate the items of a description (see ``finance.descriptions``).
_ITEM_BREAKS = (",", ";", "+")
# The amount is always in pesos: "super 2000 pesos" is just "super".
_CURRENCY_WORDS = {"peso", "pesos", "ars"}
# Which way the money went when there is no "+" or "-": a transfer can be received
# ("me transfirieron") or sent ("le transferí", "hice una transferencia").
_INCOME_PHRASES = (
    "recibi",
    "cobre",
    "me pagaron",
    "me transfirieron",
    "me depositaron",
    "me mandaron",
    "me enviaron",
    "me pasaron",
    "me llego",
    "me llegaron",
    "me devolvieron",
)
_EXPENSE_PHRASES = (
    "pague",
    "gaste",
    "compre",
    "transferi",
    "envie",
    "mande",
    "le pase",
    "le di",
    "hice una transferencia",
    "hice un pago",
    "hice una compra",
)


def is_simple_entry(text: str) -> bool:
    """One amount and a few words, like ``uber 2000`` or ``super 15.430,50 efectivo``.

    Longer messages or several numbers ("press 4 de 12 con 60") are ambiguous: when the AI
    is available they go to it instead of becoming an expense by accident.
    """
    tokens = text.split()
    return len(tokens) <= MAX_SIMPLE_ENTRY_TOKENS and len(find_amounts(tokens)) == 1


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
            if index > 0 and normalize(tokens[index - 1]) == "el":
                used.add(index - 1)  # "el miércoles", "el 15/09"
            break

    if kind is None:
        kind = _direction(tokens)
    words: list[str] = []
    item_ended = False
    for index, token in enumerate(tokens):
        if index not in used and _is_description_word(word := token.strip(_EDGE_PUNCTUATION)):
            # "coca, doritos 3000": the comma between items stays in the words.
            if item_ended and words:
                words[-1] += ","
            words.append(word)
            item_ended = False
        item_ended = item_ended or token.endswith(_ITEM_BREAKS)
    return ParsedEntry(
        amount_cents=amount.cents,
        words=tuple(words),
        kind=kind,
        day=day,
    )


def _direction(tokens: list[str]) -> TransactionKind | None:
    """Income or expense when the words say so ("recibí", "pagué"); None if unclear."""
    text = f" {normalize(' '.join(tokens))} "
    income = any(f" {phrase} " in text for phrase in _INCOME_PHRASES)
    expense = any(f" {phrase} " in text for phrase in _EXPENSE_PHRASES)
    if income == expense:
        return None
    return TransactionKind.INCOME if income else TransactionKind.EXPENSE


def _is_description_word(word: str) -> bool:
    return any(char.isalnum() for char in word) and fold(word) not in _CURRENCY_WORDS
