from asistente.finance.matching import find_phrase

PHRASES = {"uber": "transporte", "pedidos ya": "comida", "ya": "otra", "mp": "mercado pago"}


def test_finds_single_word() -> None:
    match = find_phrase(["viaje", "Uber"], PHRASES)

    assert match is not None
    assert (match.value, match.start, match.end) == ("transporte", 1, 2)


def test_prefers_longer_phrases() -> None:
    match = find_phrase(["Pedidos", "Ya", "cena"], PHRASES)

    assert match is not None
    assert (match.value, match.start, match.end) == ("comida", 0, 2)


def test_matches_phrase_written_as_one_token() -> None:
    match = find_phrase(["pedidos-ya"], PHRASES)

    assert match is not None
    assert match.value == "comida"


def test_no_match() -> None:
    assert find_phrase(["kiosco"], PHRASES) is None
    assert find_phrase([], PHRASES) is None
