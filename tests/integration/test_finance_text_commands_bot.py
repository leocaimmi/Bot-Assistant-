from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.finance.models import Transaction
from tests.harness import BotHarness


async def _amounts(session_factory: async_sessionmaker[AsyncSession]) -> list[int]:
    async with session_factory() as session:
        return list(
            await session.scalars(select(Transaction.amount_cents).order_by(Transaction.id))
        )


async def test_delete_by_text_asks_for_confirmation(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("uber 2000")
    await harness.send("sube 1500")

    await harness.send("eliminar uber 2000")
    assert "¿Borrar este movimiento?" in harness.last_reply
    assert "uber" in harness.last_reply
    assert await _amounts(session_factory) == [200_000, 150_000]

    await harness.click(harness.button("Sí, borrar"))
    assert await _amounts(session_factory) == [150_000]


async def test_delete_the_latest(harness: BotHarness) -> None:
    await harness.send("uber 2000")
    await harness.send("gym 47.000")

    await harness.send("borrar el último")

    assert "Gimnasio · gym" in harness.last_reply


async def test_edit_opens_the_editor(harness: BotHarness) -> None:
    await harness.send("uber 2000")

    await harness.send("cambiar uber 2000")

    assert "¿Qué querés cambiar?" in harness.last_reply
    harness.button("Importe")


async def test_edit_amount_category_and_day(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("uber 2000")

    await harness.send("cambiar uber 2000 a 2500")
    assert "¿Aplico este cambio?" in harness.last_reply
    assert "Importe: $2.000 → $2.500" in harness.last_reply
    assert await _amounts(session_factory) == [200_000]  # nothing changes before the OK
    await harness.click(harness.button("Aplicar"))
    assert "Movimiento actualizado" in harness.last_reply
    assert await _amounts(session_factory) == [250_000]

    await harness.send("cambiar uber a comida")
    assert "Categoría: 🚗 Transporte → 🍔 Comida" in harness.last_reply
    await harness.click(harness.button("Aplicar"))
    assert "🍔 Comida" in harness.last_reply

    await harness.send("corregir uber a ayer")
    assert "Fecha:" in harness.last_reply

    await harness.send("cambiar uber a efectivo")
    assert "Cuenta: 📱 Mercado Pago → 💵 Efectivo" in harness.last_reply
    await harness.click(harness.button("Cancelar"))
    assert "Cambio descartado" in harness.last_reply


async def test_no_match_and_missing_target(harness: BotHarness) -> None:
    await harness.send("borrar netflix 9999")
    assert "No encontré un movimiento que coincida con «netflix 9999»" in harness.last_reply

    await harness.send("borrar")
    assert "Decime cuál" in harness.last_reply


async def test_cambio_de_aceite_is_still_an_expense(harness: BotHarness) -> None:
    await harness.send("cambio de aceite 30000")

    assert "Gasto registrado" in harness.last_reply
