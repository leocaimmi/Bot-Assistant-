import pytest

from asistente.core.money import find_amounts, format_ars, parse_amount


@pytest.mark.parametrize(
    ("text", "cents"),
    [
        ("2000", 200_000),
        ("2.000", 200_000),
        ("47.000", 4_700_000),
        ("200.000", 20_000_000),
        ("1.500.000", 150_000_000),
        ("1.500,50", 150_050),
        ("1,500.50", 150_050),
        ("1500,5", 150_050),
        ("1500.25", 150_025),
        ("1,500", 150_000),
        ("$2000", 200_000),
        ("2k", 200_000),
        ("1,5k", 150_000),
        ("2.5K", 250_000),
        ("200 mil", 20_000_000),
        ("2 lucas", 200_000),
        ("1 palo", 100_000_000),
        ("1,5 millones", 150_000_000),
        ("3m", 300_000_000),
        ("2000.", 200_000),
    ],
)
def test_parse_amount(text: str, cents: int) -> None:
    assert parse_amount(text) == cents


@pytest.mark.parametrize(
    "text",
    [
        "",
        "abc",
        "0",
        "0,00",
        "1.50.000",
        "1234.567",
        "1.2345",
        "12,5,0",
        "2x10",
        "60kg",
        "200 mil uber",
    ],
)
def test_parse_amount_rejects_invalid_input(text: str) -> None:
    with pytest.raises(ValueError, match="not an amount"):
        parse_amount(text)


def test_parse_amount_rejects_absurd_values() -> None:
    with pytest.raises(ValueError, match="not an amount"):
        parse_amount("999999999999999")


def test_find_amounts_reports_token_spans() -> None:
    matches = find_amounts(["sube", "200", "mil", "y", "uber", "2.500"])

    assert [(m.start, m.end, m.cents) for m in matches] == [(1, 3, 20_000_000), (5, 6, 250_000)]


@pytest.mark.parametrize(
    ("cents", "expected"),
    [
        (200_000, "$2.000"),
        (150_050, "$1.500,50"),
        (5, "$0,05"),
        (100_000_000_000, "$1.000.000.000"),
        (-200_000, "-$2.000"),
        (0, "$0"),
    ],
)
def test_format_ars(cents: int, expected: str) -> None:
    assert format_ars(cents) == expected


def test_format_ars_signed() -> None:
    assert format_ars(200_000, signed=True) == "+$2.000"
    assert format_ars(-200_000, signed=True) == "-$2.000"
