"""Shared builders for test objects."""

from typing import Any

from asistente.config import Settings

TEST_BOT_TOKEN = "123456:TEST-not-a-real-token-000000000000000"
ALLOWED_USER_ID = 111
STRANGER_USER_ID = 999


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
