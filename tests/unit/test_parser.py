from datetime import date

import pytest

from asistente.finance.models import TransactionKind
from asistente.finance.parser import MissingAmountError, is_simple_entry, parse_entry

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
    ("text", "day"),
    [("nafta 30k el miércoles", date(2026, 9, 30)), ("nafta 30k el 15/09", date(2026, 9, 15))],
)
def test_reads_a_day_after_el(text: str, day: date) -> None:
    entry = parse_entry(text, today=TODAY)

    assert entry.day == day
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


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("recibí transferencia de juan 5000", TransactionKind.INCOME),
        ("me pagaron 50.000", TransactionKind.INCOME),
        ("hice una transferencia a juan 5000", TransactionKind.EXPENSE),
        ("le transferí 5000 a juan", TransactionKind.EXPENSE),
        ("transferencia utn 200.000", None),
        ("pagué lo que me pagaron 5000", None),
        ("+ 5000 pagué", TransactionKind.INCOME),
    ],
)
def test_words_say_which_way_the_money_went(text: str, kind: TransactionKind | None) -> None:
    assert parse_entry(text, today=TODAY).kind is kind


@pytest.mark.parametrize(
    ("text", "words"),
    [
        ("Uber, 2000.", ("Uber",)),
        ("super 2.000 pesos", ("super",)),
        ("café (efectivo) 500 ARS", ("café", "efectivo")),
    ],
)
def test_punctuation_and_currency_stay_out_of_the_words(text: str, words: tuple[str, ...]) -> None:
    assert parse_entry(text, today=TODAY).words == words


@pytest.mark.parametrize(
    ("text", "words"),
    [
        ("coca, doritos 3000", ("coca,", "doritos")),
        ("coca; doritos 3000", ("coca,", "doritos")),
        ("coca + doritos 3000", ("coca,", "doritos")),
        ("coca 2000, doritos", ("coca,", "doritos")),
        ("coca, efectivo, 2000", ("coca,", "efectivo")),
    ],
)
def test_commas_between_items_stay_in_the_words(text: str, words: tuple[str, ...]) -> None:
    assert parse_entry(text, today=TODAY).words == words


@pytest.mark.parametrize("text", ["hola", "", "uber", "gym 4x10"])
def test_requires_an_amount(text: str) -> None:
    with pytest.raises(MissingAmountError):
        parse_entry(text, today=TODAY)


@pytest.mark.parametrize(
    ("text", "simple"),
    [
        ("uber 2000", True),
        ("transferencia utn 200.000", True),
        ("super 15.430,50 efectivo", True),
        ("+ 50000 venta bici", True),
        ("pago 200 mil", True),
        ("3 cafés 6000", False),
        ("gasté dos lucas en el super", False),
        ("hoy hice press plano 4 de 12 con 60 y fondos 3 de 10", False),
    ],
)
def test_is_simple_entry(text: str, simple: bool) -> None:
    assert is_simple_entry(text) is simple
