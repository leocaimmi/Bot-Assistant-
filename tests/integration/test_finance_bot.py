from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.bot.handlers.finance import views
from asistente.bot.handlers.finance.callbacks import TxAction, TxCallback
from asistente.finance.models import Transaction
from tests.harness import BotHarness


async def _amounts(session_factory: async_sessionmaker[AsyncSession]) -> list[int]:
    async with session_factory() as session:
        return list(
            await session.scalars(select(Transaction.amount_cents).order_by(Transaction.id))
        )


async def test_registers_expense_from_plain_text(harness: BotHarness) -> None:
    await harness.send("uber 2000")

    reply = harness.last_reply
    assert "Gasto registrado" in reply
    assert "<b>$2.000</b>" in reply
    assert "Transporte · uber" in reply
    assert "Mercado Pago" in reply
    harness.button("Categoría")


async def test_registers_income(harness: BotHarness) -> None:
    await harness.send("transferencia utn 200.000")

    assert "Ingreso registrado" in harness.last_reply
    assert "$200.000" in harness.last_reply


async def test_escapes_user_text(harness: BotHarness) -> None:
    await harness.send("<b>uber</b> 2000")

    assert "&lt;b&gt;uber&lt;/b&gt;" in harness.last_reply


async def test_explains_format_when_there_is_no_amount(harness: BotHarness) -> None:
    await harness.send("hola")

    assert "No te entendí" in harness.last_reply
    assert "uber 2000" in harness.last_reply


async def test_change_category_with_buttons(harness: BotHarness) -> None:
    await harness.send("uber 2000")

    await harness.click(harness.button("Categoría"))
    await harness.click(harness.button("Gimnasio"))

    assert "Gimnasio · uber" in harness.last_reply
    assert "Categoría actualizada" in harness.alerts


async def test_edit_amount_conversation(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("uber 2000")
    await harness.click(harness.button("Editar"))
    await harness.click(harness.button("Importe"))
    assert harness.last_reply == views.ASK_AMOUNT

    await harness.send("mucho")
    assert harness.last_reply == views.INVALID_AMOUNT

    await harness.send("2.500")
    assert "Movimiento actualizado" in harness.last_reply
    assert "$2.500" in harness.last_reply
    assert await _amounts(session_factory) == [250_000]


async def test_edit_day_conversation(harness: BotHarness) -> None:
    await harness.send("uber 2000")
    await harness.click(harness.button("Editar"))
    await harness.click(harness.button("Fecha"))

    await harness.send("15/09")

    assert "📅 15/09/" in harness.last_reply


async def test_a_command_abandons_the_edit(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("uber 2000")
    await harness.click(harness.button("Editar"))
    await harness.click(harness.button("Importe"))

    await harness.send("/movimientos")
    await harness.send("sube 1500")

    assert "Gasto registrado" in harness.last_reply
    assert await _amounts(session_factory) == [200_000, 150_000]


async def test_cancel_abandons_the_edit(harness: BotHarness) -> None:
    await harness.send("uber 2000")
    await harness.click(harness.button("Editar"))
    await harness.click(harness.button("Descripción"))

    await harness.send("/cancelar")

    assert harness.last_reply == "Listo, cancelado. ✋"


async def test_delete_requires_confirmation(
    harness: BotHarness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("uber 2000")

    await harness.click(harness.button("Borrar"))
    assert "¿Borrar este movimiento?" in harness.last_reply
    assert await _amounts(session_factory) == [200_000]

    await harness.click(harness.button("Sí, borrar"))
    assert "borrado" in harness.last_reply
    assert await _amounts(session_factory) == []


async def test_toggle_kind(harness: BotHarness) -> None:
    await harness.send("transferencia 1000")
    await harness.click(harness.button("Editar"))

    await harness.click(harness.button("Es un gasto"))

    assert "Gasto" in harness.last_reply
    assert "Ahora es un gasto" in harness.alerts


async def test_list_and_paginate(harness: BotHarness) -> None:
    for amount in range(1, 13):
        await harness.send(f"uber {amount}000")

    await harness.send("/movimientos")
    assert "Página 1 de 2 · 12 en total" in harness.last_reply

    await harness.click(harness.button("Siguiente"))
    assert "Página 2 de 2" in harness.last_reply

    await harness.click(harness.button("#1"))
    assert "<b>$1.000</b>" in harness.last_reply


async def test_list_by_month(harness: BotHarness) -> None:
    await harness.send("/movimientos septiembre 2020")
    assert "No hay movimientos" in harness.last_reply

    await harness.send("/movimientos marzoo")
    assert harness.last_reply == views.INVALID_MONTH


async def test_stale_button_shows_alert(harness: BotHarness) -> None:
    await harness.click(TxCallback(action=TxAction.OPEN, tx_id=999).pack())

    assert "Ese movimiento ya no existe." in harness.alerts
