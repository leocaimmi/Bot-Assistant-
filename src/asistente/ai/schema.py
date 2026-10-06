"""The only shape the AI can answer with (enforced by OpenAI Structured Outputs).

Fields are short and few on purpose: the schema is sent with every request and its size
is billed as input tokens. Values stay as the user wrote them (amounts as text, dates as
"ayer" or "15/09"): the bot's own deterministic parsers turn them into numbers and dates.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from asistente.gym.models import MuscleGroup


def _drop_titles(schema: dict[str, Any]) -> None:
    # Pydantic adds a "title" to the model and every field: tokens that say nothing new.
    schema.pop("title", None)
    for field in schema.get("properties", {}).values():
        field.pop("title", None)


class Intent(StrEnum):
    REGISTER = "register"
    EDIT = "edit"
    DELETE = "delete"
    WORKOUT = "workout"
    REMINDER = "reminder"
    UNKNOWN = "unknown"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra=_drop_titles)


class Movement(_Strict):
    description: str = Field(description="Short, user's words, no amount/date/account")
    amount: str = Field(description="Digits, Argentine format: 2000, 200.000, 1.500,50")
    income: bool = Field(
        description="True if received (cobré, me transfirieron); false if paid or sent"
    )
    day: str | None = Field(description="hoy, ayer, anteayer or dd/mm as written")
    account: str | None = Field(description="Only if mentioned: mp, efectivo, banco")


class Target(_Strict):
    """How to find an existing movement."""

    description: str | None
    amount: str | None
    day: str | None
    latest: bool = Field(description="True for the last one, or if it is not said which")


class Changes(_Strict):
    """Only the fields that change; null otherwise."""

    amount: str | None
    description: str | None
    category: str | None = Field(description="One of the given categories")
    day: str | None
    time: str | None = Field(description="24h HH:MM")
    account: str | None = Field(description="mp, efectivo or banco")


class ExerciseDone(_Strict):
    name: str = Field(description="Reuse a known exercise name when it is the same exercise")
    muscle_group: MuscleGroup
    sets: int = Field(description="First number of 4x12")
    reps: int = Field(description="Second number of 4x12")
    weight_kg: float | None


class ReminderRequest(_Strict):
    text: str = Field(description="What to remember, short, in the user's words")
    when: str = Field(description="Only the timing, in the words listed for reminders")


class Interpretation(_Strict):
    intent: Intent
    movements: list[Movement]
    target: Target | None
    changes: Changes | None
    exercises: list[ExerciseDone]
    workout_day: str | None
    reminder: ReminderRequest | None
