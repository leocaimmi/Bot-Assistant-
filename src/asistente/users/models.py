from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from asistente.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    """A Telegram user of the bot. Only the Telegram id is stored (data minimization)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
