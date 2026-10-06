"""Reads payments that repeat every month, the way they are said in Argentina.

- Installments: ``zapatillas 10.000 cuota 1 de 9`` (also ``cuota 1/9``, ``1 de 9`` or
  ``9 cuotas de 10.000``): the amount is one installment and the first number is the one
  being paid now. ``zapatillas 90.000 en 9 cuotas`` gives the whole price, split in 9.
- Fixed payments: ``seguro del celu 5.000 todos los meses`` (also ``cada mes``,
  ``mensual``, ``fijo``), with no end. ``el 10 de cada mes`` or ``todos los 10`` also
  says the day.

Only the repeating part is read here; the rest is a normal movement ("zapatillas 10.000").
"""

import re
from dataclasses import dataclass

from asistente.finance.models import MAX_INSTALLMENTS


@dataclass(frozen=True, slots=True)
class RecurringRequest:
    text: str  # the movement itself: "zapatillas 10.000"
    installments: int | None  # how many in total; None for a fixed payment
    number: int  # the installment paid now (1 for a fixed payment)
    split_total: bool  # "en 9 cuotas": the amount is the whole price
    day_of_month: int | None  # only fixed payments with a day ("el 10 de cada mes")


# "cuota 1 de 9", "cuota 1/9"
_INSTALLMENT = re.compile(r"\bcuota\s+(?P<number>\d{1,3})\s*(?:de|/)\s*(?P<total>\d{1,3})\b", re.I)
# "en 9 cuotas" splits the price; "en 9 cuotas de 10.000" gives each one.
_IN_INSTALLMENTS = re.compile(r"\ben\s+(?P<total>\d{1,3})\s+cuotas(?P<each>\s+de)?\b", re.I)
# "9 cuotas de 10.000"
_INSTALLMENTS_OF = re.compile(r"\b(?P<total>\d{1,3})\s+cuotas\s+de\b", re.I)
# "1 de 9", but not "10 de cada mes"
_NUMBER_OF = re.compile(r"\b(?P<number>\d{1,3})\s+de\s+(?P<total>\d{1,3})\b(?![.,]\d)", re.I)
_DAY = re.compile(
    r"\b(?:el\s+)?(?P<day>\d{1,2})\s+de\s+cada\s+mes\b"
    r"|\btodos\s+los\s+(?P<other_day>\d{1,2})\b(?!\s*(?:minutos?|horas?|d[ií]as?|meses))",
    re.I,
)
_MONTHLY = re.compile(
    r"\b(?:todos\s+los\s+meses|cada\s+mes|mensual(?:es|mente)?|(?:gastos?|pagos?)\s+fijos?|fijos?)\b",
    re.I,
)


def parse_recurring(text: str) -> RecurringRequest | None:
    """The repeating payment in ``text``, or ``None`` if it does not repeat (or is unclear)."""
    rest = text
    installment: tuple[int, int, bool] | None = None  # number, total, split_total
    for pattern in (_INSTALLMENT, _IN_INSTALLMENTS, _INSTALLMENTS_OF, _NUMBER_OF):
        matches = list(pattern.finditer(rest))
        if not matches:
            continue
        if installment is not None or len(matches) > 1:
            return None  # two ways of saying it: unclear
        match = matches[0]
        groups = match.groupdict()
        number = int(groups.get("number") or 1)
        split_total = pattern is _IN_INSTALLMENTS and not groups.get("each")
        installment = (number, int(match["total"]), split_total)
        rest = _remove(rest, match)

    days = list(_DAY.finditer(rest))
    if len(days) > 1:
        return None
    if days:  # first, so "el 10 de cada mes" is not also read as "cada mes"
        rest = _remove(rest, days[0])
    monthly = list(_MONTHLY.finditer(rest))
    if installment is not None and (days or monthly):
        return None
    day = int(days[0]["day"] or days[0]["other_day"]) if days else None
    for match in reversed(monthly):  # from the end, so earlier positions stay valid
        rest = _remove(rest, match)
    rest = " ".join(rest.split())

    if installment is not None:
        number, total, split_total = installment
        if not (2 <= total <= MAX_INSTALLMENTS and 1 <= number <= total):
            return None
        return RecurringRequest(rest, total, number, split_total, day_of_month=None)
    if day is None and not monthly:
        return None
    if day is not None and not 1 <= day <= 31:
        return None
    return RecurringRequest(rest, None, 1, split_total=False, day_of_month=day)


def _remove(text: str, match: re.Match[str]) -> str:
    return f"{text[: match.start()]} {text[match.end() :]}"
