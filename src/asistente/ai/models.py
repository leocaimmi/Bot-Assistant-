from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from asistente.db.base import Base, TimestampMixin


class AiUsage(TimestampMixin, Base):
    """AI requests, tokens and cost per user and day, to see what the AI costs."""

    __tablename__ = "ai_usage"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    requests: Mapped[int] = mapped_column(default=0)
    input_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    output_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    # Priced when each request is made, so changing the model later keeps past costs right.
    cost_micro_usd: Mapped[int] = mapped_column(BigInteger, default=0, server_default=text("0"))
