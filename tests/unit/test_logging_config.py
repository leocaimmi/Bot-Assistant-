import logging
import sys
from datetime import UTC, datetime

from asistente.logging_config import REDACTED, RedactingFormatter
from tests.factories import BUENOS_AIRES

SECRET = "123456:super-secret-token"


def _record(message: str, *args: object) -> logging.LogRecord:
    return logging.LogRecord("test", logging.INFO, __file__, 1, message, args, None)


def test_masks_secret_in_message_arguments() -> None:
    formatter = RedactingFormatter("%(message)s", [SECRET])

    rendered = formatter.format(_record("calling https://api.telegram.org/bot%s/getMe", SECRET))

    assert SECRET not in rendered
    assert f"bot{REDACTED}/getMe" in rendered


def test_masks_url_encoded_secret() -> None:
    formatter = RedactingFormatter("%(message)s", [SECRET])

    rendered = formatter.format(_record("url=bot123456%3Asuper-secret-token"))

    assert "super-secret-token" not in rendered


def test_masks_secret_inside_traceback() -> None:
    formatter = RedactingFormatter("%(message)s", [SECRET])
    try:
        raise RuntimeError(f"request failed for {SECRET}")
    except RuntimeError:
        record = logging.LogRecord("test", logging.ERROR, __file__, 1, "boom", None, sys.exc_info())

    rendered = formatter.format(record)

    assert "RuntimeError" in rendered
    assert SECRET not in rendered


def test_ignores_empty_secrets() -> None:
    formatter = RedactingFormatter("%(message)s", [""])

    assert formatter.format(_record("nothing to hide")) == "nothing to hide"


def test_timestamps_use_the_bot_time_zone_with_its_offset() -> None:
    formatter = RedactingFormatter("%(asctime)s %(message)s", [], BUENOS_AIRES)
    record = _record("hola")
    record.created = datetime(2026, 10, 6, 3, 32, 10, 123_000, tzinfo=UTC).timestamp()

    assert formatter.format(record) == "2026-10-06 00:32:10.123-03:00 hola"
