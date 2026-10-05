"""The real OpenAI SDK against a fake HTTP transport: checks what is sent, at no cost."""

from collections.abc import Callable

import httpx2
import openai
import pytest

from asistente.ai.transcriber import (
    PROMPT,
    OpenAITranscriber,
    TranscriberError,
    clean_transcript,
)

AUDIO = b"OggS fake voice note"

Handler = Callable[[httpx2.Request], httpx2.Response]


def _transcriber(handler: Handler, model: str = "gpt-4o-mini-transcribe") -> OpenAITranscriber:
    client = openai.AsyncOpenAI(
        api_key="sk-test-not-a-real-key",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
        max_retries=0,
    )
    return OpenAITranscriber(client, model)


def _field(name: str, value: str) -> bytes:
    return f'name="{name}"\r\n\r\n{value}\r\n'.encode()


async def test_sends_the_voice_note_with_spanish_context() -> None:
    bodies: list[bytes] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/v1/audio/transcriptions"
        bodies.append(request.read())
        return httpx2.Response(200, json={"text": "  Uber   2000. "})

    text = await _transcriber(handler).transcribe(AUDIO)

    (body,) = bodies
    assert _field("model", "gpt-4o-mini-transcribe") in body
    assert _field("language", "es") in body
    assert _field("prompt", PROMPT) in body
    assert _field("response_format", "json") in body
    assert b'filename="voice.ogg"\r\nContent-Type: audio/ogg\r\n\r\n' + AUDIO in body
    assert text == "Uber 2000."


async def test_gpt_transcribe_gets_a_list_of_languages() -> None:
    bodies: list[bytes] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(request.read())
        return httpx2.Response(200, json={"text": "uber 2000"})

    await _transcriber(handler, model="gpt-transcribe").transcribe(AUDIO)

    (body,) = bodies
    assert _field("languages[]", "es") in body
    assert b'name="language"' not in body


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(500, json={"error": {"message": "boom"}}),
        httpx2.Response(401, json={"error": {"message": "bad key"}}),
        httpx2.Response(400, json={"error": {"message": "invalid file format"}}),
    ],
)
async def test_failures_become_transcriber_errors(response: httpx2.Response) -> None:
    transcriber = _transcriber(lambda _request: response)

    with pytest.raises(TranscriberError):
        await transcriber.transcribe(AUDIO)


@pytest.mark.parametrize(
    ("transcript", "cleaned"),
    [
        ("Uber 2000.", "Uber 2000"),
        ("Súper, 15.430,50 pesos.", "Súper, 15.430,50 pesos"),
        (
            "Pecho: banco plano 4x12 con 60 kilos. Inclinado con mancuerna 3x8.",
            "Pecho: banco plano 4x12 con 60 kilos\nInclinado con mancuerna 3x8",
        ),
        ("¿Cuánto gasté?", "¿Cuánto gasté"),
        ("...", ""),
    ],
)
def test_clean_transcript(transcript: str, cleaned: str) -> None:
    assert clean_transcript(transcript) == cleaned
