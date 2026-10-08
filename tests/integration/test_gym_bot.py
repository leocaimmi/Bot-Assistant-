from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.handlers.gym import views
from asistente.finance.models import Transaction
from asistente.gym.models import WorkoutEntry
from tests.harness import BotHarness


async def _count(session_factory: async_sessionmaker[AsyncSession], model: type[object]) -> int:
    async with session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model)) or 0


async def test_logs_the_users_example(harness: BotHarness) -> None:
    await harness.send("hice pecho: banco plano 4x12 60kg, inclinado con mancuerna 3x8")

    reply = harness.last_reply
    assert "Entrenamiento anotado" in reply
    assert "<b>Pecho</b>" in reply
    assert "• Banco plano: 4x12 · 60 kg" in reply
    assert "• Inclinado con mancuerna: 3x8" in reply
    harness.button("Deshacer")


async def test_workouts_win_over_amounts(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("banco plano 4x12 60")

    assert "Entrenamiento anotado" in harness.last_reply
    assert await _count(session_factory, Transaction) == 0


async def test_gym_fee_is_still_an_expense(harness: BotHarness) -> None:
    await harness.send("gym 47.000")

    assert "Gasto registrado" in harness.last_reply


async def test_malformed_workout_shows_the_format(harness: BotHarness) -> None:
    await harness.send("pecho: banco plano 4x12, y algo más")

    assert harness.last_reply == views.WORKOUT_FORMAT_HELP


async def test_undo(harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]) -> None:
    await harness.send("pecho: banco plano 4x12 60kg, fondos 3x10")

    await harness.click(harness.button("Deshacer"))

    assert "2 ejercicios borrados" in harness.last_reply
    assert await _count(session_factory, WorkoutEntry) == 0


async def test_day_view_and_delete_entry(harness: BotHarness) -> None:
    await harness.send("pecho: banco plano 4x12 60kg, fondos 3x10")

    await harness.send("/entreno")
    assert "1. Banco plano: 4x12 · 60 kg" in harness.last_reply
    assert "2. Fondos: 3x10" in harness.last_reply

    await harness.click(harness.button("✏️ 1"))
    assert "🏋️ <b>Banco plano</b> · Pecho\n4x12 · 60 kg" in harness.last_reply

    await harness.click(harness.button("Borrar"))
    assert "Banco plano" not in harness.last_reply
    assert "1. Fondos: 3x10" in harness.last_reply


async def test_day_view_of_another_day(harness: BotHarness) -> None:
    await harness.send("ayer piernas: sentadilla 4x10 80kg")

    await harness.send("/entreno ayer")
    assert "Sentadilla: 4x10 · 80 kg" in harness.last_reply

    await harness.send("/entreno")
    assert "No anotaste nada ese día." in harness.last_reply

    await harness.send("/entreno cualquier cosa")
    assert harness.last_reply == views.INVALID_DAY


async def test_week_history_and_exercises(harness: BotHarness) -> None:
    await harness.send("pecho: banco plano 4x12 60kg")
    await harness.send("pecho: banco plano 4x8 70kg")
    await harness.send("triceps: fondos 3x10")

    await harness.send("/semana")
    assert "Pecho, Tríceps · 11 series" in harness.last_reply
    assert "1 día entrenado" in harness.last_reply

    await harness.send("/historial banco plano")
    assert "🏆 Récord: 4x8 · 70 kg" in harness.last_reply

    await harness.send("/ejercicios")
    assert "<b>Pecho</b>: Banco plano" in harness.last_reply
    assert "<b>Tríceps</b>: Fondos" in harness.last_reply


async def test_history_usage_and_unknown_exercise(harness: BotHarness) -> None:
    await harness.send("/historial")
    assert harness.last_reply == views.HISTORY_USAGE

    await harness.send("/historial curl martillo")
    assert "No encontré ese ejercicio" in harness.last_reply


async def test_exercise_names_are_escaped(harness: BotHarness) -> None:
    await harness.send("pecho: <b>press</b> 4x12")

    assert "&lt;b&gt;press&lt;/b&gt;" in harness.last_reply


async def test_correct_an_exercise_from_the_day(harness: BotHarness) -> None:
    await harness.send("hombros: vuelos laterales 3x10, press militar 3x8 40kg")
    await harness.send("/entreno")
    await harness.click(harness.button("✏️ 1"))

    await harness.click(harness.button("Corregir"))
    assert harness.last_reply == views.ASK_VALUES
    await harness.send("7,5")

    reply = harness.last_reply
    assert reply.startswith(views.UPDATED)
    assert "Vuelos laterales</b> · Hombros\n3x10 · 7,5 kg" in reply

    await harness.click(harness.button("Volver al día"))
    assert "1. Vuelos laterales: 3x10 · 7,5 kg" in harness.last_reply
    assert "2. Press militar: 3x8 · 40 kg" in harness.last_reply


async def test_correct_sets_and_remove_the_weight(harness: BotHarness) -> None:
    await harness.send("banco plano 4x12 60kg")
    await harness.send("/entreno")
    await harness.click(harness.button("✏️ 1"))
    await harness.click(harness.button("Corregir"))

    await harness.send("no sé")
    assert harness.last_reply == views.INVALID_VALUES

    await harness.send("4x10 sin peso")
    assert "4x10 · sin peso" in harness.last_reply

    await harness.send("uber 2000")  # the step ended: this is a new movement
    assert "Gasto registrado" in harness.last_reply


async def test_cancel_a_correction(harness: BotHarness) -> None:
    await harness.send("banco plano 4x12 60kg")
    await harness.send("/entreno")
    await harness.click(harness.button("✏️ 1"))
    await harness.click(harness.button("Corregir"))

    await harness.send("/cancelar")
    await harness.send("/entreno")

    assert "Banco plano: 4x12 · 60 kg" in harness.last_reply


async def test_old_delete_buttons_do_nothing(harness: BotHarness) -> None:
    await harness.send("banco plano 4x12 60kg")
    await harness.send("/entreno")
    entry_id = harness.button("✏️ 1").rsplit(":", 1)[1]

    await harness.click(f"ge:{entry_id}")  # the old "🗑 1" button deleted right away
    await harness.send("/entreno")

    assert harness.alerts[-1] == "Este botón ya no está disponible."
    assert "Banco plano" in harness.last_reply
