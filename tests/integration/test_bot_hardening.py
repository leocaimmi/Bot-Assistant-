"""Hostile or odd input must never break the bot nor inject markup."""

from tests.harness import BotHarness


async def test_forged_button_data_is_ignored(harness: BotHarness) -> None:
    await harness.click("sum:2026:13")
    await harness.click("txp:0:1500:3")

    assert harness.alerts == ["Este botón ya no está disponible."] * 2


async def test_category_names_cannot_inject_markup(harness: BotHarness) -> None:
    await harness.send("/nueva_categoria <b>Auto")
    assert "🏷️ &lt;b&gt;Auto" in harness.last_reply

    await harness.send("/nueva_categoria <b>auto")
    assert "Ya existe la categoría 🏷️ &lt;b&gt;Auto." in harness.last_reply

    await harness.send("/categorias")
    assert "&lt;b&gt;Auto" in harness.last_reply
