from datetime import UTC, datetime, timedelta

from asistente.bot.handlers.gym import views
from tests.harness import BotHarness

THURSDAY = datetime(2026, 10, 8, 16, 40, tzinfo=UTC)  # 13:40 in Buenos Aires
WEDNESDAY = THURSDAY - timedelta(days=1)
SHOULDERS = "hombros: press militar con barra 3x8 40kg, vuelos laterales con mancuerna 3x10"


async def test_users_example(harness: BotHarness) -> None:
    await harness.send(SHOULDERS, at=WEDNESDAY)
    await harness.send("uber 2000", at=THURSDAY)

    await harness.send("Quiero cambiar algo del entrenamiento del miércoles", at=THURSDAY)

    reply = harness.last_reply
    assert "Entrenamiento de mié 07/10/2026" in reply
    assert "2. Vuelos laterales con mancuerna: 3x10" in reply
    await harness.click(harness.button("✏️ 2"))
    await harness.click(harness.button("Corregir"))
    await harness.send("7,5", at=THURSDAY)
    assert "Vuelos laterales con mancuerna</b> · Hombros\n3x10 · 7,5 kg" in harness.last_reply


async def test_a_fix_is_shown_before_it_is_made(harness: BotHarness) -> None:
    await harness.send(SHOULDERS, at=WEDNESDAY)

    await harness.send("al press militar del miércoles ponele 42,5 kilos", at=THURSDAY)

    reply = harness.last_reply
    assert "¿Aplico este cambio?" in reply
    assert "3x8 · 40 kg → <b>3x8 · 42,5 kg</b>" in reply
    assert "📅 mié 07/10/2026" in reply
    apply = harness.button("Aplicar")
    await harness.click(apply)
    assert harness.last_reply.startswith(views.UPDATED)
    assert "3x8 · 42,5 kg" in harness.last_reply

    await harness.click(apply)  # the same button twice applies nothing
    assert harness.alerts[-1] == views.CHANGE_UNAVAILABLE


async def test_a_fix_can_be_cancelled(harness: BotHarness) -> None:
    await harness.send(SHOULDERS, at=WEDNESDAY)
    await harness.send("cambiar press militar a 3x10", at=THURSDAY)

    await harness.click(harness.button("Cancelar"))
    await harness.send("/entreno 07/10", at=THURSDAY)

    assert harness.replies[-2] == views.CHANGE_DISCARDED
    assert "Press militar con barra: 3x8 · 40 kg" in harness.last_reply


async def test_unclear_values_show_the_exercise(harness: BotHarness) -> None:
    await harness.send(SHOULDERS, at=WEDNESDAY)

    await harness.send("el press militar eran 3x10 no 3x8", at=THURSDAY)

    assert "Press militar con barra</b> · Hombros\n3x8 · 40 kg" in harness.last_reply
    harness.button("Corregir")


async def test_nothing_to_change(harness: BotHarness) -> None:
    await harness.send("editar la rutina", at=THURSDAY)
    assert harness.last_reply == views.NOTHING_LOGGED

    await harness.send(SHOULDERS, at=WEDNESDAY)
    await harness.send("cambiar press militar a 40kg", at=THURSDAY)
    assert harness.last_reply.startswith(views.ALREADY_LIKE_THAT)

    await harness.send("cambiar el entrenamiento de hoy", at=THURSDAY)
    assert "No anotaste nada ese día." in harness.last_reply


async def test_the_gym_fee_is_still_a_movement(harness: BotHarness) -> None:
    await harness.send("gym 47.000", at=THURSDAY)
    await harness.send(SHOULDERS, at=THURSDAY)

    await harness.send("borrar el gym", at=THURSDAY)

    assert "¿Borrar este movimiento?" in harness.last_reply
