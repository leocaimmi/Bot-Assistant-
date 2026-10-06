from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from asistente.db.base import Base, TimestampMixin
from asistente.db.types import UTCDateTime

MAX_DESCRIPTION_LENGTH = 120
MAX_INSTALLMENTS = 120  # ten years of monthly payments


class TransactionKind(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


def _kind_column_type() -> Enum:
    # Stored as VARCHAR + CHECK constraint, portable across databases.
    return Enum(
        TransactionKind,
        name="transaction_kind",
        native_enum=False,
        create_constraint=True,
        length=10,
        values_callable=lambda kinds: [kind.value for kind in kinds],
        validate_strings=True,
    )


class Account(TimestampMixin, Base):
    """Where money moves: Mercado Pago, cash, a bank account..."""

    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(40))
    emoji: Mapped[str] = mapped_column(String(8))
    # Normalized words that select this account in a message, e.g. ["mp", "mercado pago"].
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_default: Mapped[bool] = mapped_column(default=False)


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(40))
    emoji: Mapped[str] = mapped_column(String(8))
    kind: Mapped[TransactionKind] = mapped_column(_kind_column_type())
    # Used when no keyword matches ("Otros gastos" / "Otros ingresos").
    is_fallback: Mapped[bool] = mapped_column(default=False)

    keywords: Mapped[list["CategoryKeyword"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="CategoryKeyword.keyword",
        lazy="raise",
    )

    @property
    def label(self) -> str:
        return f"{self.emoji} {self.name}"


class CategoryKeyword(Base):
    """A normalized word that assigns a category, e.g. ``uber`` -> Transporte."""

    __tablename__ = "category_keywords"
    # A keyword points to exactly one category per user.
    __table_args__ = (UniqueConstraint("user_id", "keyword"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    keyword: Mapped[str] = mapped_column(String(40))

    category: Mapped[Category] = relationship(back_populates="keywords", lazy="raise")


class Transaction(TimestampMixin, Base):
    """An expense or an income. The amount is always positive; ``kind`` gives the sign."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_positive"),
        Index("ix_transactions_user_id_occurred_at", "user_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[TransactionKind] = mapped_column(_kind_column_type())
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(String(MAX_DESCRIPTION_LENGTH), default="")
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime())

    account: Mapped[Account] = relationship(lazy="raise")
    category: Mapped[Category] = relationship(lazy="raise")

    @property
    def signed_cents(self) -> int:
        return self.amount_cents if self.kind is TransactionKind.INCOME else -self.amount_cents


class RecurringPayment(TimestampMixin, Base):
    """A movement the bot registers by itself every month: installments or a fixed payment.

    Installments stop after ``installments`` charges ("zapatillas 2/9"); a fixed payment
    (``installments`` is NULL, e.g. "seguro del celu") goes on until it is cancelled.
    """

    __tablename__ = "recurring_payments"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_positive"),
        CheckConstraint("day_of_month BETWEEN 1 AND 31", name="day_of_month_range"),
        CheckConstraint(
            f"installments IS NULL OR installments BETWEEN 2 AND {MAX_INSTALLMENTS}",
            name="installments_range",
        ),
        CheckConstraint("next_number >= 1", name="next_number_positive"),
        # The scheduler looks for active payments that are due.
        Index("ix_recurring_payments_active_next_run_at", "active", "next_run_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    description: Mapped[str] = mapped_column(String(MAX_DESCRIPTION_LENGTH), default="")
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    day_of_month: Mapped[int]  # the last day in shorter months
    installments: Mapped[int | None]  # how many in total; NULL for a fixed payment
    next_number: Mapped[int]  # the next charge: 2 in "2/9"
    next_run_at: Mapped[datetime] = mapped_column(UTCDateTime())
    active: Mapped[bool] = mapped_column(default=True)

    account: Mapped[Account] = relationship(lazy="raise")
    category: Mapped[Category] = relationship(lazy="raise")

    def label(self, number: int) -> str:
        """Description of charge ``number``: "zapatillas (2/9)" or the fixed description."""
        return installment_label(self.description, number, self.installments)


def installment_label(description: str, number: int, installments: int | None) -> str:
    """``zapatillas (2/9)``, always within the description length limit."""
    if installments is None:
        return description
    suffix = f"({number}/{installments})"
    base = description[: MAX_DESCRIPTION_LENGTH - len(suffix) - 1].rstrip()
    return f"{base} {suffix}" if base else suffix
