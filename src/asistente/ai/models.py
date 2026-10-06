from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from asistente.db.base import Base, TimestampMixin


class AiUsage(TimestampMixin, Base):
    """AI requests (text and voice), tokens and cost per user and day."""

    __tablename__ = "ai_usage"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    requests: Mapped[int] = mapped_column(default=0)  # text interpretations
    input_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    output_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    transcriptions: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    audio_seconds: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    # Priced when each request is made, so changing the model later keeps past costs right.
    cost_micro_usd: Mapped[int] = mapped_column(BigInteger, default=0, server_default=text("0"))
