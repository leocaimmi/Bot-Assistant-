"""Imports every model so ``Base.metadata`` describes the full schema (used by Alembic)."""

from asistente.db.base import Base
from asistente.finance.models import Account, Category, CategoryKeyword, Transaction
from asistente.users.models import User

__all__ = ["Account", "Base", "Category", "CategoryKeyword", "Transaction", "User"]
