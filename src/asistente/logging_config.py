"""Logging setup that masks secrets even if they end up inside a message or traceback."""

import logging
import sys
from collections.abc import Iterable
from urllib.parse import quote

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
REDACTED = "***"


class RedactingFormatter(logging.Formatter):
    """Formatter that replaces known secret values in the fully rendered log line."""

    def __init__(self, fmt: str, secrets: Iterable[str]) -> None:
        super().__init__(fmt)
        variants = {variant for secret in secrets if secret for variant in _variants(secret)}
        # Longest first, so a secret containing another one is fully masked.
        self._secrets = sorted(variants, key=len, reverse=True)

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        for secret in self._secrets:
            rendered = rendered.replace(secret, REDACTED)
        return rendered


def _variants(secret: str) -> set[str]:
    # Secrets may also appear URL-encoded, e.g. inside a request URL.
    return {secret, quote(secret, safe="")}


def setup_logging(level: str, secrets: Iterable[str] = ()) -> None:
    """Log to stdout (what container platforms collect) with secret redaction."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(RedactingFormatter(LOG_FORMAT, secrets))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
