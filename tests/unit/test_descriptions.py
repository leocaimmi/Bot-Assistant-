import pytest

from asistente.finance.descriptions import description_items, format_description


@pytest.mark.parametrize(
    ("text", "formatted"),
    [
        ("uber", "Uber"),
        ("Gym Megatlon", "Gym megatlon"),
        ("una coca, Doritos picantes y un chocolate", "Coca, Doritos picantes, Chocolate"),
        ("coca, doritos, chocolate", "Coca, Doritos, Chocolate"),
        ("coca; doritos", "Coca, Doritos"),
        ("coca + doritos", "Coca, Doritos"),
        ("pan y queso", "Pan y queso"),  # without a list, "y" is part of the item
        ("la luz", "Luz"),
        ("la", "La"),  # only an article: kept
        ("transferencia UTN", "Transferencia UTN"),  # acronyms keep their capitals
        ("nafta YPF, peaje", "Nafta YPF, Peaje"),
        ("pan 3,5kg", "Pan 3,5kg"),  # a decimal comma is not a separator
        ("  muchos   espacios  ", "Muchos espacios"),
        ("coca, , doritos,", "Coca, Doritos"),
        ("café, agua e ibuprofeno", "Café, Agua, Ibuprofeno"),
        ("", ""),
    ],
)
def test_format_description(text: str, formatted: str) -> None:
    assert format_description(text) == formatted


def test_formatting_twice_changes_nothing() -> None:
    once = format_description("una coca, Doritos picantes y un chocolate")

    assert format_description(once) == once


def test_description_items() -> None:
    assert description_items("Coca, Doritos picantes, Chocolate") == [
        "Coca",
        "Doritos picantes",
        "Chocolate",
    ]
    assert description_items("Uber") == ["Uber"]
    assert description_items("") == []
