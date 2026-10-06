from datetime import date

import pytest

from asistente.finance.commands import (
    CommandKind,
    TargetQuery,
    TextCommand,
    looks_like_correction,
    parse_command,
    parse_target,
    split_new_value,
)

TODAY = date(2026, 10, 5)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("borrar uber 2000", TextCommand(CommandKind.DELETE, "uber 2000")),
        ("Eliminá el gym", TextCommand(CommandKind.DELETE, "el gym")),
        ("anular netflix", TextCommand(CommandKind.DELETE, "netflix")),
        ("cambiar uber 2000 a 2500", TextCommand(CommandKind.EDIT, "uber 2000 a 2500")),
        ("Corregí el super", TextCommand(CommandKind.EDIT, "el super")),
        ("borrar", TextCommand(CommandKind.DELETE, "")),
    ],
)
def test_parse_command(text: str, expected: TextCommand) -> None:
    assert parse_command(text) == expected


@pytest.mark.parametrize("text", ["uber 2000", "cambio de aceite 30000", "sacar plata 5000", ""])
def test_regular_entries_are_not_commands(text: str) -> None:
    assert parse_command(text) is None


def test_split_new_value() -> None:
    assert split_new_value("uber 2000 a 2500") == ("uber 2000", "2500")
    assert split_new_value("transferencia a juan a 3000") == ("transferencia a juan", "3000")
    assert split_new_value("uber 2000") is None
    assert split_new_value("a 2500") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("uber 2000", TargetQuery(("uber",), 200_000, None, latest=False)),
        ("el uber de ayer", TargetQuery(("uber",), None, date(2026, 10, 4), latest=False)),
        ("el último", TargetQuery((), None, None, latest=True)),
        ("la ultima transferencia", TargetQuery(("transferencia",), None, None, latest=True)),
        ("Pedidos-Ya 8.500", TargetQuery(("pedidos", "ya"), 850_000, None, latest=False)),
    ],
)
def test_parse_target(text: str, expected: TargetQuery) -> None:
    assert parse_target(text, TODAY) == expected


def test_empty_target() -> None:
    assert parse_target("el de", TODAY).is_empty
    assert not parse_target("el último", TODAY).is_empty


@pytest.mark.parametrize(
    ("text", "correction"),
    [
        ("el uber eran 2500", True),
        ("el gym era 50 lucas", True),
        ("en vez de 2000 fueron 2500", True),
        ("me equivoqué con el super", True),
        ("uber 2000", False),
        ("cena con amigos 15000", False),
    ],
)
def test_looks_like_correction(text: str, correction: bool) -> None:
    assert looks_like_correction(text) is correction
