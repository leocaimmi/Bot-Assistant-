from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asistente.ai.schema import Intent
from asistente.ai.transcriber import TranscriberError
from asistente.bot.handlers import fallback, voice
from asistente.finance.models import Transaction
from tests.ai_factories import FakeInterpreter, FakeTranscriber, interpretation, movement
from tests.factories import STRANGER_USER_ID
from tests.harness import FAKE_AUDIO, BotHarness


async def _descriptions(session_factory: async_sessionmaker[AsyncSession]) -> list[str | None]:
    async with session_factory() as session:
        query = select(Transaction.description).order_by(Transaction.id)
        return list(await session.scalars(query))


async def test_shows_what_it_heard_and_the_rules_register_it(
    ai_harness: BotHarness,
    fake_transcriber: FakeTranscriber,
    fake_interpreter: FakeInterpreter,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    fake_transcriber.will_hear("Uber, 2000 pesos.")

    await ai_harness.send_voice(duration=3)

    heard, registered = ai_harness.replies
    assert heard == "🎙 <i>Uber, 2000 pesos.</i>"
    assert "Gasto registrado" in registered
    assert "🚗 Transporte · Uber" in registered
    assert fake_transcriber.audios == [FAKE_AUDIO]
    assert fake_interpreter.texts == []  # the rules understood it: no second request
    assert await _descriptions(session_factory) == ["Uber"]


async def test_a_dictated_workout_is_logged(
    ai_harness: BotHarness, fake_transcriber: FakeTranscriber
) -> None:
    fake_transcriber.will_hear(
        "Pecho: banco plano 4 por 12 con 60 kilos. Inclinado con mancuerna 3x8."
    )

    await ai_harness.send_voice(duration=8)

    assert "Entrenamiento anotado" in ai_harness.last_reply
    assert "Banco plano: 4x12 · 60 kg" in ai_harness.last_reply
    assert "Inclinado con mancuerna: 3x8" in ai_harness.last_reply


async def test_a_command_by_voice(
    ai_harness: BotHarness, fake_transcriber: FakeTranscriber
) -> None:
    await ai_harness.send("uber 2000")
    fake_transcriber.will_hear("Borrar el Uber de 2000.")

    await ai_harness.send_voice()

    assert "¿Borrar este movimiento?" in ai_harness.last_reply


async def test_what_the_rules_do_not_understand_goes_to_the_ai(
    ai_harness: BotHarness, fake_transcriber: FakeTranscriber, fake_interpreter: FakeInterpreter
) -> None:
    fake_transcriber.will_hear("Gasté dos lucas en el súper.")
    fake_interpreter.will_answer(
        interpretation(Intent.REGISTER, movements=[movement("súper", "2000")])
    )

    await ai_harness.send_voice()

    assert fake_interpreter.texts == ["Gasté dos lucas en el súper"]
    assert "Gasto registrado" in ai_harness.last_reply


async def test_errors_after_transcribing_keep_the_usage(
    ai_harness: BotHarness, fake_transcriber: FakeTranscriber
) -> None:
    fake_transcriber.will_hear("Borrar netflix.")

    await ai_harness.send_voice(duration=4)
    assert "No encontré un movimiento que coincida con «netflix»" in ai_harness.last_reply

    await ai_harness.send("/ia")
    assert "🎙 1 audio (gpt-4o-mini-transcribe): 4 s" in ai_harness.last_reply


async def test_long_voice_notes_are_not_downloaded(
    ai_harness: BotHarness, fake_transcriber: FakeTranscriber
) -> None:
    await ai_harness.send_voice(duration=61)
    assert ai_harness.last_reply == voice.VOICE_TOO_LONG

    await ai_harness.send_voice(duration=10, file_size=5_000_000)
    assert ai_harness.last_reply == voice.VOICE_TOO_LONG

    assert ai_harness.session.downloads == 0
    assert fake_transcriber.audios == []


async def test_failures_and_silence(
    ai_harness: BotHarness, fake_transcriber: FakeTranscriber
) -> None:
    fake_transcriber.will_hear(TranscriberError(), "", "...")

    await ai_harness.send_voice()
    assert ai_harness.last_reply == voice.VOICE_FAILED

    await ai_harness.send_voice()
    assert ai_harness.last_reply == voice.VOICE_EMPTY

    await ai_harness.send_voice()
    assert ai_harness.last_reply == voice.VOICE_EMPTY


async def test_voice_counts_in_the_daily_limit_and_usage(
    ai_harness: BotHarness, fake_transcriber: FakeTranscriber, fake_interpreter: FakeInterpreter
) -> None:
    # The limit is 3: a voice note the rules understand takes 1, one for the AI takes 2.
    fake_transcriber.will_hear("uber 2000", "gasté dos lucas en el súper")
    fake_interpreter.will_answer(
        interpretation(Intent.REGISTER, movements=[movement("súper", "2000")])
    )
    await ai_harness.send_voice(duration=12)
    await ai_harness.send_voice(duration=8)

    await ai_harness.send_voice()
    assert "límite de 3 consultas" in ai_harness.last_reply
    assert ai_harness.session.downloads == 2

    await ai_harness.send("/ia")
    assert "Hoy: 3 de 3 consultas" in ai_harness.last_reply
    assert "💬 1 texto (gpt-6-luna)" in ai_harness.last_reply
    assert "🎙 2 audios (gpt-4o-mini-transcribe): 20 s" in ai_harness.last_reply
    # 20 s of audio (1000) and one interpretation (120), in micro-dollars
    assert "Costo estimado: US$ 0,0011" in ai_harness.last_reply


async def test_without_ai_voice_is_explained(harness: BotHarness) -> None:
    await harness.send_voice()

    assert harness.last_reply == voice.VOICE_DISABLED
    assert harness.session.downloads == 0


async def test_while_editing_it_asks_for_a_typed_answer(
    ai_harness: BotHarness, fake_transcriber: FakeTranscriber
) -> None:
    await ai_harness.send("uber 2000")
    await ai_harness.click(ai_harness.button("Editar"))
    await ai_harness.click(ai_harness.button("Importe"))

    await ai_harness.send_voice()

    assert ai_harness.last_reply == fallback.VOICE_WHILE_BUSY
    assert fake_transcriber.audios == []


async def test_strangers_voice_is_ignored(ai_harness: BotHarness) -> None:
    await ai_harness.send_voice(user_id=STRANGER_USER_ID)

    assert ai_harness.replies == []
    assert ai_harness.session.downloads == 0
