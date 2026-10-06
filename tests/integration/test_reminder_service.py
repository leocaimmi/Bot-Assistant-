from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.reminders.parser import ParsedReminder, parse_reminder
from asistente.reminders.service import (
    MAX_ACTIVE_REMINDERS,
    MissingReminderTextError,
    ReminderInThePastError,
    ReminderNotFoundError,
    ReminderService,
    ReminderTextTooLongError,
    TooManyRemindersError,
)
from asistente.users.models import User
from asistente.users.service import UserService
from tests.factories import BUENOS_AIRES

# Monday 5 October 2026, 10:00 in Buenos Aires.
NOW = datetime(2026, 10, 5, 10, 0, tzinfo=BUENOS_AIRES)


def _parsed(message: str, now: datetime = NOW) -> ParsedReminder:
    parsed = parse_reminder(message, now, BUENOS_AIRES)
    assert parsed is not None, message
    return parsed


@pytest.fixture
def reminders(session: AsyncSession) -> ReminderService:
    return ReminderService(session)


async def test_create_and_list_the_next_one_first(reminders: ReminderService, user: User) -> None:
    later = await reminders.create(user, _parsed("recordame mañana a las 9 pagar la luz"), now=NOW)
    sooner = await reminders.create(user, _parsed("recordame en 20 minutos la ropa"), now=NOW)

    assert [r.id for r in await reminders.active(user)] == [sooner.id, later.id]
    assert later.text == "pagar la luz"
    assert later.next_run_at == datetime(2026, 10, 6, 9, tzinfo=BUENOS_AIRES)
    assert later.timezone == "America/Argentina/Buenos_Aires"


@pytest.mark.parametrize(
    ("message", "error"),
    [
        ("recordame mañana a las 9", MissingReminderTextError),
        (f"recordame mañana {'x' * 201}", ReminderTextTooLongError),
        ("recordame hoy a las 8 algo", ReminderInThePastError),
    ],
)
async def test_rejects_invalid_reminders(
    reminders: ReminderService, user: User, message: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        await reminders.create(user, _parsed(message), now=NOW)


async def test_limits_the_active_reminders(reminders: ReminderService, user: User) -> None:
    for _ in range(MAX_ACTIVE_REMINDERS):
        await reminders.create(user, _parsed("recordame mañana algo"), now=NOW)

    with pytest.raises(TooManyRemindersError):
        await reminders.create(user, _parsed("recordame mañana otra cosa"), now=NOW)


async def test_a_one_off_reminder_is_sent_once(reminders: ReminderService, user: User) -> None:
    reminder = await reminders.create(user, _parsed("recordame en 20 minutos la ropa"), now=NOW)
    due_time = NOW + timedelta(minutes=21)

    assert await reminders.due_ids(NOW) == []
    assert await reminders.due_ids(due_time) == [reminder.id]
    due = await reminders.claim(reminder.id, due_time)
    assert due is not None
    assert (due.reminder.id, due.chat_id) == (reminder.id, user.telegram_id)

    await reminders.advance(due.reminder, due_time)
    assert await reminders.due_ids(due_time) == []
    assert await reminders.claim(reminder.id, due_time) is None
    assert await reminders.active(user) == []


async def test_a_repeating_reminder_moves_on_and_skips_missed_runs(
    reminders: ReminderService, user: User
) -> None:
    reminder = await reminders.create(
        user, _parsed("recordame todos los lunes a las 12 la pastilla"), now=NOW
    )
    assert reminder.next_run_at == datetime(2026, 10, 5, 12, tzinfo=BUENOS_AIRES)

    # The bot was off for three weeks: the next run is the following Monday, not a burst.
    late = datetime(2026, 10, 26, 13, tzinfo=BUENOS_AIRES)
    await reminders.advance(reminder, late)

    assert reminder.active
    assert reminder.next_run_at == datetime(2026, 11, 2, 12, tzinfo=BUENOS_AIRES)


async def test_a_reminder_in_another_time_zone_repeats_there(
    reminders: ReminderService, user: User
) -> None:
    madrid = ZoneInfo("Europe/Madrid")
    reminder = await reminders.create(
        user, _parsed("recordame todos los lunes a las 10 hora de España la call"), now=NOW
    )
    assert reminder.next_run_at == datetime(2026, 10, 12, 10, tzinfo=madrid)

    await reminders.advance(reminder, reminder.next_run_at)

    # Spain leaves summer time on 25 October: still 10:00 there, an hour later here.
    assert reminder.next_run_at == datetime(2026, 10, 19, 10, tzinfo=madrid)
    await reminders.advance(reminder, datetime(2026, 10, 26, 9, tzinfo=madrid))
    assert reminder.next_run_at == datetime(2026, 10, 26, 10, tzinfo=madrid)
    assert reminder.next_run_at.astimezone(BUENOS_AIRES).hour == 6


async def test_snooze_makes_a_one_off_copy(reminders: ReminderService, user: User) -> None:
    original = await reminders.create(
        user, _parsed("recordame todos los días a las 8 tomar agua"), now=NOW
    )

    copy = await reminders.snooze(user, original.id, now=NOW)

    assert copy.id != original.id
    assert copy.text == "tomar agua"
    assert copy.next_run_at == NOW + timedelta(minutes=10)
    assert original.active


async def test_other_users_reminders_are_out_of_reach(
    session: AsyncSession, reminders: ReminderService, user: User
) -> None:
    reminder = await reminders.create(user, _parsed("recordame mañana algo"), now=NOW)
    stranger, _ = await UserService(session).get_or_create(999)

    with pytest.raises(ReminderNotFoundError):
        await reminders.get(stranger, reminder.id)
    with pytest.raises(ReminderNotFoundError):
        await reminders.delete(stranger, reminder.id)

    await reminders.delete(user, reminder.id)
    assert await reminders.active(user) == []


async def test_due_uses_utc_instants(reminders: ReminderService, user: User) -> None:
    reminder = await reminders.create(user, _parsed("recordame mañana a las 9 algo"), now=NOW)

    assert await reminders.due_ids(datetime(2026, 10, 6, 12, tzinfo=UTC)) == [reminder.id]
    assert await reminders.due_ids(datetime(2026, 10, 6, 11, 59, tzinfo=UTC)) == []
