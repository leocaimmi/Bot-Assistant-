from datetime import date

import pytest

from asistente.finance.models import TransactionKind
from asistente.finance.parser import MissingAmountError, parse_entry

TODAY = date(2026, 10, 5)


def test_simple_expense() -> None:
    entry = parse_entry("uber 2000", today=TODAY)

    assert entry.amount_cents == 200_000
    assert entry.words == ("uber",)
    assert entry.kind is None
    assert entry.day is None


def test_amount_can_come_first_and_keeps_original_spelling() -> None:
    entry = parse_entry("47.000 Gym Megatlon", today=TODAY)

    assert entry.amount_cents == 4_700_000
    assert entry.words == ("Gym", "Megatlon")


def test_reads_date_word() -> None:
    entry = parse_entry("nafta 30k ayer", today=TODAY)

    assert entry.amount_cents == 3_000_000
    assert entry.day == date(2026, 10, 4)
    assert entry.words == ("nafta",)


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("+ 50000 venta bici", TransactionKind.INCOME),
        ("-5000 transferencia", TransactionKind.EXPENSE),
    ],
)
def test_sign_forces_kind(text: str, kind: TransactionKind) -> None:
    assert parse_entry(text, today=TODAY).kind is kind


def test_largest_number_is_the_amount() -> None:
    entry = parse_entry("3 cafés 6000", today=TODAY)

    assert entry.amount_cents == 600_000
    assert entry.words == ("3", "cafés")


def test_drops_symbol_only_words() -> None:
    entry = parse_entry("uber $ 2000 !", today=TODAY)

    assert entry.words == ("uber",)


@pytest.mark.parametrize("text", ["hola", "", "uber", "gym 4x10"])
def test_requires_an_amount(text: str) -> None:
    with pytest.raises(MissingAmountError):
        parse_entry(text, today=TODAY)
