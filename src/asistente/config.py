"""Application settings, loaded from environment variables and an optional local ``.env``."""

import re
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

_BOT_TOKEN_PATTERN = re.compile(r"\d+:[A-Za-z0-9_-]{30,}")


class DatabaseSettings(BaseSettings):
    """Settings needed to reach the database. Shared by the bot and the Alembic migrations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        # Validation errors must never echo raw values: they may contain secrets.
        hide_input_in_errors=True,
    )

    database_url: SecretStr = SecretStr("sqlite+aiosqlite:///./data/asistente.db")


class Settings(DatabaseSettings):
    """Full bot configuration."""

    bot_token: SecretStr
    allowed_user_ids: Annotated[frozenset[int], NoDecode]
    timezone: str = "America/Argentina/Buenos_Aires"
    log_level: LogLevel = "INFO"

    @field_validator("bot_token")
    @classmethod
    def _validate_bot_token(cls, value: SecretStr) -> SecretStr:
        if not _BOT_TOKEN_PATTERN.fullmatch(value.get_secret_value()):
            raise ValueError("BOT_TOKEN does not look like a Telegram bot token")
        return value

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def _split_user_ids(cls, value: Any) -> Any:
        if isinstance(value, str):
            return frozenset(int(part) for part in value.split(",") if part.strip())
        return value

    @field_validator("allowed_user_ids")
    @classmethod
    def _require_user_ids(cls, value: frozenset[int]) -> frozenset[int]:
        if not value:
            raise ValueError("ALLOWED_USER_IDS needs at least one Telegram user id")
        if any(user_id <= 0 for user_id in value):
            raise ValueError("Telegram user ids must be positive integers")
        return value

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown timezone {value!r}") from exc
        return value

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def load_settings() -> Settings:
    """Build the settings from the environment; raises ``ValidationError`` when misconfigured."""
    return Settings()  # type: ignore[call-arg]  # values come from the environment
