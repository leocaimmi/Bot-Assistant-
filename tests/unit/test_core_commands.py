import pytest

from asistente.core.commands import CommandKind, command_kind, looks_like_correction


@pytest.mark.parametrize(
    ("word", "kind"),
    [("Borrá", CommandKind.DELETE), ("cambiar", CommandKind.EDIT), ("sacar", None), ("", None)],
)
def test_command_kind(word: str, kind: CommandKind | None) -> None:
    assert command_kind(word) is kind


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
