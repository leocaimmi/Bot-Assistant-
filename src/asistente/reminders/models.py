from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from asistente.core.schedule import Repeat, Schedule, mask_to_weekdays
from asistente.db.base import Base, TimestampMixin
from asistente.db.types import UTCDateTime

MAX_TEXT_LENGTH = 200


class Reminder(TimestampMixin, Base):
    """Something to remember, once or repeating; the bot sends it when it is due."""

    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint("minute_of_day BETWEEN 0 AND 1439", name="minute_of_day_range"),
        CheckConstraint("weekdays BETWEEN 0 AND 127", name="weekdays_range"),
        CheckConstraint(
            "day_of_month IS NULL OR day_of_month BETWEEN 1 AND 31", name="day_of_month_range"
        ),
        # The sender looks for active reminders that are due.
        Index("ix_reminders_active_next_run_at", "active", "next_run_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(String(MAX_TEXT_LENGTH))
    repeat: Mapped[Repeat] = mapped_column(
        Enum(
            Repeat,
            name="reminder_repeat",
            native_enum=False,
            create_constraint=True,
            length=10,
            values_callable=lambda repeats: [repeat.value for repeat in repeats],
            validate_strings=True,
        )
    )
    # Time of day in ``timezone``, as minutes after midnight.
    minute_of_day: Mapped[int]
    weekdays: Mapped[int] = mapped_column(default=0)  # WEEKLY: bit 0 is Monday
    day_of_month: Mapped[int | None]  # MONTHLY
    timezone: Mapped[str] = mapped_column(String(64))  # IANA name
    next_run_at: Mapped[datetime] = mapped_column(UTCDateTime)
    active: Mapped[bool] = mapped_column(default=True)

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def schedule(self) -> Schedule:
        weekly = self.repeat is Repeat.WEEKLY
        return Schedule(
            self.repeat,
            time(*divmod(self.minute_of_day, 60)),
            weekdays=mask_to_weekdays(self.weekdays) if weekly else frozenset(),
            day_of_month=self.day_of_month if self.repeat is Repeat.MONTHLY else None,
        )
