import pytest

from asistente.gym.units import format_kg, parse_kg


@pytest.mark.parametrize(
    ("text", "grams"),
    [("60", 60_000), ("62,5", 62_500), ("62.5", 62_500), ("0,5", 500), (" 100 ", 100_000)],
)
def test_parse_kg(text: str, grams: int) -> None:
    assert parse_kg(text) == grams


@pytest.mark.parametrize("text", ["", "abc", "0", "-5", "1001", "1,2345"])
def test_parse_kg_rejects_invalid_weights(text: str) -> None:
    assert parse_kg(text) is None


@pytest.mark.parametrize(
    ("grams", "text"),
    [(60_000, "60 kg"), (62_500, "62,5 kg"), (500, "0,5 kg"), (100_250, "100,25 kg")],
)
def test_format_kg(grams: int, text: str) -> None:
    assert format_kg(grams) == text
