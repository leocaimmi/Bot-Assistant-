"""Imports every model so ``Base.metadata`` describes the full schema (used by Alembic)."""

from asistente.db.base import Base
from asistente.users.models import User

__all__ = ["Base", "User"]
