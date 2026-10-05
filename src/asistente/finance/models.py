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
