import pytest

from tests.harness import BotHarness

TOPICS = [
    ("Gastos e ingresos", "/resumen"),
    ("Gimnasio", "/entreno"),
    ("Corregir y borrar", "borrar el último"),
    ("IA y audios", "/ia"),
]


async def test_help_menu_opens_every_topic_and_comes_back(harness: BotHarness) -> None:
    await harness.send("/ayuda")
    assert "¿Qué puedo hacer?" in harness.last_reply

    for label, expected in TOPICS:
        await harness.click(harness.button(label))
        assert expected in harness.last_reply

        await harness.click(harness.button("Menú"))
        assert "¿Qué puedo hacer?" in harness.last_reply


async def test_start_shows_the_menu(harness: BotHarness) -> None:
    await harness.send("/start")

    assert "¡Hola, Leo!" in harness.last_reply
    assert "¿Qué puedo hacer?" in harness.last_reply
    harness.button("Gimnasio")


@pytest.mark.parametrize(("ai_on", "offers_audio"), [(True, True), (False, False)])
async def test_audio_is_offered_only_with_ai(
    harness: BotHarness, ai_harness: BotHarness, ai_on: bool, offers_audio: bool
) -> None:
    bot = ai_harness if ai_on else harness

    await bot.send("/ayuda")
    assert ("audio" in bot.last_reply) is offers_audio

    await bot.click(bot.button("IA y audios"))
    assert ("apagada" in bot.last_reply) is not ai_on
