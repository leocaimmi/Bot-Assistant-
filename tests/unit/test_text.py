import pytest

from asistente.core.text import fold, normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Uber", "uber"),
        ("  Café   Martínez! ", "cafe martinez"),
        ("pedidos-ya", "pedidos ya"),
        ("AÑO", "ano"),
        ("💸", ""),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


def test_fold_keeps_punctuation() -> None:
    assert fold("Millón 1.500,50") == "millon 1.500,50"
