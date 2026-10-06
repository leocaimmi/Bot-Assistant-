import pytest

from asistente.bot.commands import BOT_COMMANDS
from asistente.bot.help import HelpTopic, help_text


def test_every_command_of_the_menu_is_explained() -> None:
    everything = "\n".join(help_text(topic, ai_enabled=True) for topic in HelpTopic)

    for command in BOT_COMMANDS:
        assert f"/{command.command}" in everything, command.command


@pytest.mark.parametrize("topic", list(HelpTopic))
@pytest.mark.parametrize("ai_enabled", [True, False])
def test_each_screen_fits_on_a_phone(topic: HelpTopic, ai_enabled: bool) -> None:
    text = help_text(topic, ai_enabled=ai_enabled)

    assert len(text.splitlines()) <= 20
    assert len(text) <= 1_000


def test_without_ai_audio_is_not_offered() -> None:
    assert "audio" in help_text(HelpTopic.MENU, ai_enabled=True)
    assert "audio" not in help_text(HelpTopic.MENU, ai_enabled=False)
    assert "apagada" in help_text(HelpTopic.AI, ai_enabled=False)
    assert "apagada" not in help_text(HelpTopic.AI, ai_enabled=True)
