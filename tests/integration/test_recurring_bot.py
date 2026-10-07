from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.handlers.common import EXAMPLES_BUTTON
from asistente.bot.handlers.recurring import views
from asistente.bot.help import HelpTopic, help_text
from asistente.finance.models import RecurringPayment, Transaction
from tests.ai_factories import FakeInterpreter
from tests.factories import BUENOS_AIRES
from tests.harness import BotHarness


async def _count(session_factory: async_sessionmaker[AsyncSession], model: type[object]) -> int:
    async with session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model)) or 0


async def test_installments_are_registered_by_the_rules(
    ai_harness: BotHarness, fake_interpreter: FakeInterpreter
) -> None:
    await ai_harness.send("zapatillas 10.000 cuota 1 de 9")

    card, plan = ai_harness.replies[-2:]
    assert "Gasto registrado" in card
    assert "Zapatillas (1/9)" in card
    assert "🔁 <b>Cuotas: Zapatillas</b> · $10.000" in plan
    assert "Te anoto la 2/9 el" in plan
    assert "hasta la 9/9" in plan
    assert fake_interpreter.texts == []  # no AI, no tokens


async def test_fixed_payments_and_the_list(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    today = datetime.now(BUENOS_AIRES).day
    other_day = 1 if today != 1 else 2

    await harness.send("seguro del celu 5.000 todos los meses")
    assert "🔁 <b>Gasto fijo: Seguro del celu</b> · $5.000" in harness.last_reply
    assert f"el {today} de cada mes" in harness.last_reply

    await harness.send(f"alquiler 300.000 el {other_day} de cada mes")
    assert f"el {other_day} de cada mes" in harness.last_reply
    assert await _count(session_factory, Transaction) == 1  # the rent waits for its day

    await harness.send("/fijos")
    assert "🔁 <b>Cuotas y gastos fijos</b>" in harness.last_reply
    assert "Seguro del celu" in harness.last_reply
    assert "Alquiler" in harness.last_reply

    await harness.click(harness.button("🗑 1"))
    assert "2. <b>" not in harness.last_reply
    await harness.click(harness.button("🗑 1"))
    assert harness.last_reply == views.EMPTY_LIST
    assert harness.button(EXAMPLES_BUTTON)
    assert await _count(session_factory, RecurringPayment) == 2  # kept, but cancelled


async def test_the_last_installment(harness: BotHarness) -> None:
    await harness.send("zapatillas 10.000 cuota 9 de 9")

    assert "Zapatillas (9/9)" in harness.replies[-2]
    assert harness.last_reply == views.LAST_INSTALLMENT


async def test_an_empty_list_offers_the_examples_in_a_button(harness: BotHarness) -> None:
    await harness.send("/fijos")

    assert harness.last_reply == views.EMPTY_LIST
    assert "<code>" not in harness.last_reply

    await harness.click(harness.button(EXAMPLES_BUTTON))
    assert harness.last_reply == help_text(HelpTopic.RECURRING, ai_enabled=False)
