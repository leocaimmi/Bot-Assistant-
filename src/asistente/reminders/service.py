"""A user's reminders (create, list, delete, snooze) and the ones that are due for everyone."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.core.errors import UserError
from asistente.core.schedule import Repeat, next_occurrence, weekdays_to_mask
from asistente.reminders.models import MAX_TEXT_LENGTH, Reminder
from asistente.reminders.parser import ParsedReminder
from asistente.users.models import User

MAX_ACTIVE_REMINDERS = 30  # they all fit in one /recordatorios message
SNOOZE_MINUTES = 10
DUE_BATCH = 50


class MissingReminderTextError(UserError):
    def __init__(self) -> None:
        super().__init__(
            "🤔 ¿Qué te recuerdo? Por ejemplo: <code>recordame mañana a las 9 pagar la luz</code>."
        )


class ReminderTextTooLongError(UserError):
    def __init__(self) -> None:
        super().__init__(f"El recordatorio es muy largo: hasta {MAX_TEXT_LENGTH} caracteres.")


class ReminderInThePastError(UserError):
    def __init__(self) -> None:
        super().__init__(
            "⌛ Esa hora ya pasó. Decime otra, por ejemplo <code>mañana a las 9</code>."
        )


class TooManyRemindersError(UserError):
    def __init__(self) -> None:
        super().__init__(
            f"Ya tenés {MAX_ACTIVE_REMINDERS} recordatorios: borrá alguno en /recordatorios."
        )


class ReminderNotFoundError(UserError):
    def __init__(self) -> None:
        super().__init__("Ese recordatorio ya no existe.")


@dataclass(frozen=True, slots=True)
class DueReminder:
    reminder: Reminder
    chat_id: int  # private chats: the user's Telegram id


class ReminderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User, parsed: ParsedReminder, *, now: datetime) -> Reminder:
        if not parsed.text:
            raise MissingReminderTextError
        if len(parsed.text) > MAX_TEXT_LENGTH:
            raise ReminderTextTooLongError
        if parsed.first_run <= now:
            raise ReminderInThePastError
        if await self._count_active(user) >= MAX_ACTIVE_REMINDERS:
            raise TooManyRemindersError
        schedule = parsed.schedule
        reminder = Reminder(
            user_id=user.id,
            text=parsed.text,
            repeat=schedule.repeat,
            minute_of_day=schedule.at.hour * 60 + schedule.at.minute,
            weekdays=weekdays_to_mask(schedule.weekdays),
            day_of_month=schedule.day_of_month,
            timezone=parsed.timezone,
            next_run_at=parsed.first_run,
            active=True,
        )
        self._session.add(reminder)
        await self._session.flush()
        return reminder

    async def active(self, user: User) -> list[Reminder]:
        """Pending reminders, the next one first."""
        query = (
            select(Reminder)
            .where(Reminder.user_id == user.id, Reminder.active.is_(True))
            .order_by(Reminder.next_run_at, Reminder.id)
        )
        return list(await self._session.scalars(query))

    async def get(self, user: User, reminder_id: int) -> Reminder:
        reminder = await self._session.scalar(
            select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user.id)
        )
        if reminder is None:
            raise ReminderNotFoundError
        return reminder

    async def delete(self, user: User, reminder_id: int) -> None:
        await self._session.delete(await self.get(user, reminder_id))
        await self._session.flush()

    async def snooze(self, user: User, reminder_id: int, *, now: datetime) -> Reminder:
        """A one-off copy of the reminder, due in a few minutes (the original is kept)."""
        original = await self.get(user, reminder_id)
        if await self._count_active(user) >= MAX_ACTIVE_REMINDERS:
            raise TooManyRemindersError
        run = (now + timedelta(minutes=SNOOZE_MINUTES)).astimezone(original.zone)
        copy = Reminder(
            user_id=user.id,
            text=original.text,
            repeat=Repeat.ONCE,
            minute_of_day=run.hour * 60 + run.minute,
            weekdays=0,
            day_of_month=None,
            timezone=original.timezone,
            next_run_at=run,
            active=True,
        )
        self._session.add(copy)
        await self._session.flush()
        return copy

    async def due_ids(self, now: datetime, *, limit: int = DUE_BATCH) -> list[int]:
        """Reminders of every user that are due, the oldest first."""
        query = (
            select(Reminder.id)
            .where(Reminder.active.is_(True), Reminder.next_run_at <= now)
            .order_by(Reminder.next_run_at)
            .limit(limit)
        )
        return list(await self._session.scalars(query))

    async def claim(self, reminder_id: int, now: datetime) -> DueReminder | None:
        """The reminder and where to send it, if it is still active and due."""
        row = (
            await self._session.execute(
                select(Reminder, User.telegram_id)
                .join(User, User.id == Reminder.user_id)
                .where(
                    Reminder.id == reminder_id,
                    Reminder.active.is_(True),
                    Reminder.next_run_at <= now,
                )
            )
        ).one_or_none()
        return DueReminder(reminder=row[0], chat_id=row[1]) if row is not None else None

    async def advance(self, reminder: Reminder, now: datetime) -> None:
        """After sending: a one-off reminder is done; a repeating one moves to its next run.

        Runs missed while the bot was off are skipped, so they are not sent in a burst.
        """
        if reminder.repeat is Repeat.ONCE:
            reminder.active = False
        else:
            after = max(now, reminder.next_run_at).astimezone(reminder.zone)
            next_run = next_occurrence(reminder.schedule, after)
            if next_run is None:  # pragma: no cover - repeating schedules always run again
                reminder.active = False
            else:
                reminder.next_run_at = next_run
        await self._session.flush()

    async def turn_off(self, reminder_id: int) -> None:
        """Stop a reminder that cannot be sent (used by the sender, not by users)."""
        reminder = await self._session.get(Reminder, reminder_id)
        if reminder is not None:
            reminder.active = False
            await self._session.flush()

    async def _count_active(self, user: User) -> int:
        query = (
            select(func.count())
            .select_from(Reminder)
            .where(Reminder.user_id == user.id, Reminder.active.is_(True))
        )
        return await self._session.scalar(query) or 0
