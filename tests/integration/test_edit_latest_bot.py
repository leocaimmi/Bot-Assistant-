from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.handlers import latest
from asistente.finance.models import Transaction
from asistente.gym.models import WorkoutEntry
from tests.ai_factories import FakeInterpreter
from tests.harness import BotHarness

THURSDAY = datetime(2026, 10, 8, 16, 40, tzinfo=UTC)  # 13:40 in Buenos Aires
EARLIER, LATER = THURSDAY, THURSDAY + timedelta(minutes=1)


async def _registered_at(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    movements: datetime,
    workouts: datetime,
) -> None:
    """Fix when everything was registered: two messages a millisecond apart could tie."""
    async with session_factory() as session, session.begin():
        await session.execute(update(Transaction).values(created_at=movements))
        await session.execute(update(WorkoutEntry).values(created_at=workouts))


async def test_the_workout_just_logged(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("uber 2000", at=THURSDAY)
    await harness.send("ayer hombros: press militar 3x8, vuelos laterales 3x10", at=THURSDAY)
    await _registered_at(session_factory, movements=EARLIER, workouts=LATER)

    await harness.send("Quiero editar algo", at=THURSDAY + timedelta(minutes=1))

    assert "Entrenamiento de mié 07/10/2026" in harness.last_reply
    assert "2. Vuelos laterales: 3x10" in harness.last_reply
    harness.button("✏️ 2")


async def test_the_movement_just_registered(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("pecho: banco plano 4x12", at=THURSDAY)
    await harness.send("uber 2000", at=THURSDAY)
    await _registered_at(session_factory, movements=LATER, workouts=EARLIER)

    await harness.send("me equivoqué", at=THURSDAY + timedelta(minutes=1))

    assert "¿Qué querés cambiar?" in harness.last_reply
    assert "$2.000" in harness.last_reply
    harness.button("Importe")


async def test_nothing_logged_yet(harness: BotHarness) -> None:
    await harness.send("quiero corregir algo")

    assert harness.last_reply == latest.NOTHING_TO_EDIT


async def test_vague_edits_never_call_the_ai(
    ai_harness: BotHarness, fake_interpreter: FakeInterpreter
) -> None:
    await ai_harness.send("uber 2000")

    await ai_harness.send("Quiero editar algo")

    assert fake_interpreter.texts == []
    assert "¿Qué querés cambiar?" in ai_harness.last_reply
