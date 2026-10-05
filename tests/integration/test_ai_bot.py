from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.ai.interpreter import InterpreterError
from asistente.ai.schema import Intent
from asistente.bot.app import build_dispatcher
from asistente.bot.handlers import assistant
from asistente.bot.handlers.free_text import CORRECTION_HELP, NOT_UNDERSTOOD
from asistente.finance.models import Transaction
from asistente.gym.models import MuscleGroup, WorkoutEntry
from tests.ai_factories import (
    FakeInterpreter,
    changes,
    exercise,
    interpretation,
    movement,
    target,
)
from tests.factories import make_settings
from tests.harness import BotHarness


async def _amounts(session_factory: async_sessionmaker[AsyncSession]) -> list[int]:
    async with session_factory() as session:
        query = select(Transaction.amount_cents).order_by(Transaction.id)
        return list(await session.scalars(query))


async def test_rules_never_call_the_ai(
    ai_harness: BotHarness, fake_interpreter: FakeInterpreter
) -> None:
    await ai_harness.send("uber 2000")
    await ai_harness.send("pecho: banco plano 4x12 60kg")
    await ai_harness.send("borrar uber 2000")

    assert fake_interpreter.texts == []


async def test_registers_a_free_form_expense(
    ai_harness: BotHarness, fake_interpreter: FakeInterpreter
) -> None:
    fake_interpreter.will_answer(
        interpretation(Intent.REGISTER, movements=[movement("super", "2000")])
    )

    await ai_harness.send("gasté dos lucas en el super")

    assert "Gasto registrado" in ai_harness.last_reply
    assert "🛒 Supermercado · super" in ai_harness.last_reply
    assert "$2.000" in ai_harness.last_reply
    context = fake_interpreter.contexts[0]
    assert "Transporte" in context.categories


async def test_rejects_an_amount_the_user_did_not_write(
    ai_harness: BotHarness,
    fake_interpreter: FakeInterpreter,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    fake_interpreter.will_answer(
        interpretation(Intent.REGISTER, movements=[movement("algo", "9999")])
    )

    await ai_harness.send("pagué algo, eran 2000 me parece")

    assert ai_harness.last_reply == CORRECTION_HELP
    assert await _amounts(session_factory) == []


async def test_edit_shows_a_preview_and_applies_on_confirmation(
    ai_harness: BotHarness,
    fake_interpreter: FakeInterpreter,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await ai_harness.send("uber 2000")
    fake_interpreter.will_answer(
        interpretation(Intent.EDIT, target=target("uber", "2000"), changes=changes(amount="2500"))
    )

    await ai_harness.send("el uber de 2000 eran 2500")
    assert "¿Aplico este cambio?" in ai_harness.last_reply
    assert "Importe: $2.000 → $2.500" in ai_harness.last_reply
    assert await _amounts(session_factory) == [200_000]

    await ai_harness.click(ai_harness.button("Aplicar"))
    assert "Movimiento actualizado" in ai_harness.last_reply
    assert await _amounts(session_factory) == [250_000]


async def test_edit_can_be_cancelled(
    ai_harness: BotHarness,
    fake_interpreter: FakeInterpreter,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await ai_harness.send("uber 2000")
    fake_interpreter.will_answer(
        interpretation(Intent.EDIT, target=target("uber"), changes=changes(category="Comida"))
    )

    await ai_harness.send("el uber en realidad era comida")
    assert "Categoría: 🚗 Transporte → 🍔 Comida" in ai_harness.last_reply
    cancel = ai_harness.button("Cancelar")
    apply = ai_harness.button("Aplicar")

    await ai_harness.click(cancel)
    assert "Cambio descartado" in ai_harness.last_reply

    await ai_harness.click(apply)
    assert "Este cambio ya no está disponible." in ai_harness.alerts
    assert await _amounts(session_factory) == [200_000]


async def test_delete_asks_for_confirmation(
    ai_harness: BotHarness, fake_interpreter: FakeInterpreter
) -> None:
    await ai_harness.send("gym 47.000")
    fake_interpreter.will_answer(interpretation(Intent.DELETE, target=target("gym")))

    await ai_harness.send("sacá lo del gimnasio que cargué")

    assert "¿Borrar este movimiento?" in ai_harness.last_reply
    ai_harness.button("Sí, borrar")


async def test_missing_target_is_explained(
    ai_harness: BotHarness, fake_interpreter: FakeInterpreter
) -> None:
    fake_interpreter.will_answer(interpretation(Intent.DELETE, target=target("netflix")))

    await ai_harness.send("sacá lo de netflix")

    assert "No encontré un movimiento que coincida con «netflix»" in ai_harness.last_reply


async def test_logs_a_free_form_workout(
    ai_harness: BotHarness,
    fake_interpreter: FakeInterpreter,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    fake_interpreter.will_answer(
        interpretation(
            Intent.WORKOUT,
            exercises=[
                exercise("Press plano", 4, 12, kg=60),
                exercise("Fondos", 3, 10, group=MuscleGroup.TRICEPS),
            ],
        )
    )

    await ai_harness.send("hoy hice press plano 4 de 12 con 60 y después fondos 3 de 10")

    assert "Entrenamiento anotado" in ai_harness.last_reply
    assert "Press plano: 4x12 · 60 kg" in ai_harness.last_reply
    assert "<b>Tríceps</b>" in ai_harness.last_reply
    async with session_factory() as session:
        assert len(list(await session.scalars(select(WorkoutEntry)))) == 2


async def test_unknown_and_failures(
    ai_harness: BotHarness, fake_interpreter: FakeInterpreter
) -> None:
    fake_interpreter.will_answer(interpretation(Intent.UNKNOWN), InterpreterError())

    await ai_harness.send("hola, ¿cómo estás?")
    assert ai_harness.last_reply == NOT_UNDERSTOOD

    await ai_harness.send("otra cosa rara")
    assert ai_harness.last_reply == assistant.AI_UNAVAILABLE


async def test_daily_limit_and_usage(
    ai_harness: BotHarness, fake_interpreter: FakeInterpreter
) -> None:
    fake_interpreter.will_answer(*[interpretation(Intent.UNKNOWN)] * 3)
    for _ in range(3):
        await ai_harness.send("mensaje raro")

    await ai_harness.send("uno más")
    assert "límite de 3 interpretaciones" in ai_harness.last_reply
    assert len(fake_interpreter.texts) == 3

    await ai_harness.send("/ia")
    assert "Hoy: 3 de 3 consultas" in ai_harness.last_reply
    assert "2.700 tokens de entrada" in ai_harness.last_reply
    # 3 x (900 x 0.10 + 60 x 0.50) micro-dollars with gpt-6-luna
    assert "Costo estimado del mes: US$ 0,0004" in ai_harness.last_reply


async def test_usage_warns_about_a_model_without_a_known_price(
    session_factory: async_sessionmaker[AsyncSession], fake_interpreter: FakeInterpreter
) -> None:
    settings = make_settings(openai_api_key="sk-test", openai_model="modelo-nuevo")
    harness = BotHarness(build_dispatcher(settings, session_factory, fake_interpreter))
    fake_interpreter.will_answer(interpretation(Intent.UNKNOWN))
    await harness.send("mensaje raro")

    await harness.send("/ia")

    assert "Costo estimado del mes: US$ 0,0000" in harness.last_reply
    assert "No sé el precio de modelo-nuevo" in harness.last_reply


async def test_without_ai_corrections_are_never_registered(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("el uber eran 2500")
    assert harness.last_reply == CORRECTION_HELP
    assert await _amounts(session_factory) == []

    await harness.send("/ia")
    assert harness.last_reply == assistant.AI_DISABLED
