"""Logging setup that masks secrets even if they end up inside a message or traceback."""

import logging
import sys
from collections.abc import Iterable
from datetime import UTC, datetime, tzinfo
from urllib.parse import quote

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
REDACTED = "***"


class RedactingFormatter(logging.Formatter):
    """Formatter that replaces known secret values in the fully rendered log line."""

    def __init__(self, fmt: str, secrets: Iterable[str], tz: tzinfo = UTC) -> None:
        super().__init__(fmt)
        self._tz = tz
        variants = {variant for secret in secrets if secret for variant in _variants(secret)}
        # Longest first, so a secret containing another one is fully masked.
        self._secrets = sorted(variants, key=len, reverse=True)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802 (stdlib name)
        """``2026-10-06 00:32:10.123-03:00``: the bot's time zone, with its offset."""
        moment = datetime.fromtimestamp(record.created, self._tz)
        return moment.isoformat(sep=" ", timespec="milliseconds")

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        for secret in self._secrets:
            rendered = rendered.replace(secret, REDACTED)
        return rendered


def _variants(secret: str) -> set[str]:
    # Secrets may also appear URL-encoded, e.g. inside a request URL.
    return {secret, quote(secret, safe="")}


def setup_logging(level: str, secrets: Iterable[str] = (), tz: tzinfo = UTC) -> None:
    """Log to stdout (what container platforms collect) with secret redaction.

    Times are in ``tz`` (the bot's time zone), not in the server's clock, which is UTC in
    containers.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(RedactingFormatter(LOG_FORMAT, secrets, tz))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
