from asistente.bot.handlers.finance import views
from tests.harness import BotHarness


async def test_lists_categories_with_keywords(harness: BotHarness) -> None:
    await harness.send("/categorias")

    reply = harness.last_reply
    assert "🚗 <b>Transporte</b>: sube, uber, didi" in reply
    assert "<b>Ingresos</b>" in reply


async def test_decide_where_fuel_goes(harness: BotHarness) -> None:
    await harness.send("/nueva_categoria 🚙 Auto")
    assert "Categoría de gasto 🚙 Auto creada" in harness.last_reply

    await harness.send("/palabra nafta auto")
    assert "<b>nafta</b> → 🚙 Auto (antes estaba en 🚗 Transporte)" in harness.last_reply

    await harness.send("nafta 30k")
    assert "🚙 Auto · Nafta" in harness.last_reply


async def test_errors_are_explained(harness: BotHarness) -> None:
    await harness.send("/palabra nafta vehiculo")
    assert "No encontré esa categoría" in harness.last_reply

    await harness.send("/nueva_categoria transporte")
    assert "Ya existe la categoría 🚗 Transporte." in harness.last_reply


async def test_usage_without_arguments(harness: BotHarness) -> None:
    await harness.send("/palabra")
    assert harness.last_reply == views.KEYWORD_USAGE

    await harness.send("/nueva_categoria")
    assert harness.last_reply == views.NEW_CATEGORY_USAGE
