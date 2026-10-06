"""The OpenAI client shared by every AI feature: one connection pool, one place for limits."""

import openai

# A chat bot should answer fast or say it could not: short timeout and a single retry.
TIMEOUT_SECONDS = 20.0
MAX_RETRIES = 1


def create_client(api_key: str) -> openai.AsyncOpenAI:
    return openai.AsyncOpenAI(api_key=api_key, timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES)
