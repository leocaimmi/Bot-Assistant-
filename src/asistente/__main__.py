"""Entry point: ``python -m asistente``."""

import asyncio
import sys
from contextlib import suppress

from pydantic import ValidationError

from asistente.bot.app import run_polling
from asistente.config import load_settings
from asistente.logging_config import setup_logging


def main() -> None:
    try:
        settings = load_settings()
    except ValidationError as exc:
        # Input values are hidden in these errors, so no secret is printed.
        sys.exit(f"Invalid configuration, check your environment variables:\n{exc}")

    setup_logging(settings.log_level, secrets=[settings.bot_token.get_secret_value()])
    with suppress(KeyboardInterrupt):
        asyncio.run(run_polling(settings))


if __name__ == "__main__":
    main()
