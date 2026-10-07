"""Shared builders for test objects."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from asistente.config import Settings

TEST_BOT_TOKEN = "123456:TEST-not-a-real-token-000000000000000"
ALLOWED_USER_ID = 111
STRANGER_USER_ID = 999
BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")
# Monday 5 October 2026 at noon: answers that depend on the time of day stay the same.
MONDAY_NOON = datetime(2026, 10, 5, 12, 0, tzinfo=BUENOS_AIRES)


def make_settings(**overrides: Any) -> Settings:
    """Settings built only from explicit values (ignores any local ``.env`` file)."""
    values: dict[str, Any] = {
        "_env_file": None,
        "bot_token": TEST_BOT_TOKEN,
        "allowed_user_ids": str(ALLOWED_USER_ID),
        "database_url": "sqlite+aiosqlite:///:memory:",
        **overrides,
    }
    return Settings(**values)
