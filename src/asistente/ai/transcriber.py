"""Turns a voice message into text with one OpenAI speech-to-text request.

Cost and safety by design:
- The bot only sends short voice notes: it checks their length before downloading them.
- The audio stays in memory: it is never written to disk nor kept by the bot.
- The transcript is untrusted text: it goes through the same rules and validation as a
  typed message.
"""

import logging
import re
from typing import Protocol

import openai

logger = logging.getLogger(__name__)

LANGUAGE = "es"
# Context for the model, in the language of the audio. It has no sample amounts or
# exercises on purpose: on a silent recording a model may repeat its prompt, and a sample
# amount would be registered as a real one.
PROMPT = (
    "Mensaje de voz en español de Argentina para anotar gastos, ingresos y ejercicios del "
    "gimnasio. Los montos, las series, las repeticiones y los kilos van con números."
)

_GPT_TRANSCRIBE = re.compile(r"gpt-transcribe(?:-\d{4}-\d{2}-\d{2})?")
# A sentence ends with ".", "!" or "?" before a space or the end; "15.430,50" is not one.
_SENTENCE_END = re.compile(r"[.!?]+(?=\s|$)")


class TranscriberError(Exception):
    """The audio could not be transcribed."""


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes) -> str: ...


class OpenAITranscriber:
    def __init__(self, client: openai.AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def transcribe(self, audio: bytes) -> str:
        """Text of a Telegram voice note (OGG/Opus); empty if nothing was said."""
        # gpt-transcribe takes a list of possible languages; the other models take one.
        several_languages = _GPT_TRANSCRIBE.fullmatch(self._model) is not None
        try:
            transcription = await self._client.audio.transcriptions.create(
                model=self._model,
                # Telegram names voice files ".oga"; the API needs a known extension.
                file=("voice.ogg", audio, "audio/ogg"),
                language=openai.omit if several_languages else LANGUAGE,
                languages=[LANGUAGE] if several_languages else openai.omit,
                prompt=PROMPT,
                response_format="json",
            )
        except openai.OpenAIError as exc:
            logger.warning("Transcription failed: %s", type(exc).__name__)
            raise TranscriberError from exc
        return " ".join(transcription.text.split())


def clean_transcript(text: str) -> str:
    """Make a transcript read like a typed message, so the free rules understand it.

    Each sentence becomes a line ("4x12. Inclinado 3x8." holds two exercises) and closing
    punctuation goes away. Separators inside numbers ("15.430,50") stay.
    """
    lines = (line.strip() for line in _SENTENCE_END.split(text))
    return "\n".join(line for line in lines if line)
