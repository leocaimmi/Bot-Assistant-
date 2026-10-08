from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.handlers.common import EXAMPLES_BUTTON
from asistente.bot.handlers.reminders import views
from asistente.bot.help import HelpTopic, help_text
from asistente.finance.models import Transaction
from asistente.reminders.models import Reminder
from tests.ai_factories import FakeTranscriber
from tests.factories import BUENOS_AIRES, MONDAY_NOON
from tests.harness import BotHarness


async def _count(session_factory: async_sessionmaker[AsyncSession], model: type[object]) -> int:
    async with session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model)) or 0


async def test_creates_a_reminder_and_deletes_it(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("recordame mañana a las 9 pagar la luz", at=MONDAY_NOON)

    assert "⏰ <b>Te lo recuerdo:</b> Pagar la luz" in harness.last_reply
    assert "📅 mañana a las 9:00" in harness.last_reply
    assert await _count(session_factory, Reminder) == 1

    await harness.click(harness.button("Borrar"))
    assert harness.last_reply == views.DELETED
    assert await _count(session_factory, Reminder) == 0


async def test_late_at_night_the_card_says_the_date(harness: BotHarness) -> None:
    late_night = datetime(2026, 10, 6, 1, 29, tzinfo=BUENOS_AIRES)  # Tuesday

    await harness.send("recordame mañana a las 9 una reunión", at=late_night)
    assert "📅 hoy (mar 06/10) a las 9:00" in harness.last_reply

    await harness.send("recordame todos los días a las 12 tomar la B12", at=late_night)
    assert "· próximo: hoy (mar 06/10)" in harness.last_reply


async def test_repeating_and_other_time_zone(harness: BotHarness) -> None:
    await harness.send("recordame todos los lunes a las 12 que tengo que tomar una pastilla")
    assert "Tengo que tomar una pastilla" in harness.last_reply
    assert "🔁 todos los lunes a las 12:00 · próximo:" in harness.last_reply

    await harness.send("recordame mañana a las 10 hora de España llamar a Pablo")
    assert "🌍 hora de Madrid · acá:" in harness.last_reply


async def test_an_amount_inside_a_reminder_is_not_an_expense(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("recordame el lunes pagar 2000 de luz")

    assert "Pagar 2000 de luz" in harness.last_reply
    assert await _count(session_factory, Transaction) == 0


async def test_unclear_or_empty_reminders(harness: BotHarness) -> None:
    await harness.send("recordame pagar la luz")
    assert harness.last_reply == views.NOT_UNDERSTOOD
    await harness.click(harness.button("Ver ejemplos"))
    assert "⏰ <b>Recordatorios</b>" in harness.last_reply

    await harness.send("recordame mañana a las 9")
    assert "¿Qué te recuerdo?" in harness.last_reply


async def test_deleting_reminders_by_text_points_to_the_list(harness: BotHarness) -> None:
    await harness.send("borrar el recordatorio de la pastilla")

    assert harness.last_reply == views.USE_THE_LIST


async def test_a_dictated_reminder(
    ai_harness: BotHarness, fake_transcriber: FakeTranscriber
) -> None:
    fake_transcriber.will_hear("Recordame mañana a las 9 que tengo que pagar la luz.")

    await ai_harness.send_voice()

    assert "Te lo recuerdo:</b> Tengo que pagar la luz" in ai_harness.last_reply


async def test_list_and_delete_from_the_list(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("/recordatorios")
    assert harness.last_reply == views.EMPTY_LIST
    assert harness.button(EXAMPLES_BUTTON)

    await harness.send("recordame mañana a las 9 pagar la luz")
    await harness.send("recordame todos los lunes a las 10 hora de España la call")
    await harness.send("/recordatorios")
    assert "⏰ <b>Tus recordatorios</b>" in harness.last_reply
    assert "2. <b>" in harness.last_reply
    assert "hora de Madrid" in harness.last_reply

    await harness.click(harness.button("🗑 1"))
    assert await _count(session_factory, Reminder) == 1
    assert "1. <b>" in harness.last_reply
    assert "2. <b>" not in harness.last_reply

    await harness.click(harness.button("🗑 1"))
    assert harness.last_reply == views.EMPTY_LIST

    await harness.click(harness.button(EXAMPLES_BUTTON))
    assert harness.last_reply == help_text(HelpTopic.REMINDERS, ai_enabled=False)
