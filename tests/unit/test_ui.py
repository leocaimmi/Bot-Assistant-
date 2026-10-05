from asistente.bot.ui import split_message


def test_short_text_is_one_part() -> None:
    assert split_message("hola\nchau") == ["hola\nchau"]


def test_splits_on_line_breaks() -> None:
    text = "\n".join(["a" * 4] * 5)  # 5 lines of 4 chars, 24 chars in total

    parts = split_message(text, limit=10)

    assert parts == ["aaaa\naaaa", "aaaa\naaaa", "aaaa"]
    assert all(len(part) <= 10 for part in parts)


def test_cuts_a_line_longer_than_the_limit() -> None:
    parts = split_message("x" * 25, limit=10)

    assert parts == ["x" * 10, "x" * 10, "x" * 5]


def test_keeps_empty_lines() -> None:
    assert split_message("a\n\nb", limit=10) == ["a\n\nb"]
