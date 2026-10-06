from asistente.ai.client import create_client


async def test_client_fails_fast() -> None:
    client = create_client("sk-test-not-a-real-key")
    try:
        assert client.timeout == 20.0
        assert client.max_retries == 1
    finally:
        await client.close()
