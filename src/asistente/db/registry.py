"""Imports every model so ``Base.metadata`` describes the full schema (used by Alembic)."""

from asistente.ai.models import AiUsage
from asistente.db.base import Base
from asistente.finance.models import (
    Account,
    Category,
    CategoryKeyword,
    RecurringPayment,
    Transaction,
)
from asistente.gym.models import Exercise, Workout, WorkoutEntry
from asistente.reminders.models import Reminder
from asistente.users.models import User

__all__ = [
    "Account",
    "AiUsage",
    "Base",
    "Category",
    "CategoryKeyword",
    "Exercise",
    "RecurringPayment",
    "Reminder",
    "Transaction",
    "User",
    "Workout",
    "WorkoutEntry",
]
