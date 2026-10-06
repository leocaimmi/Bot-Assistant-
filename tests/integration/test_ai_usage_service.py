from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from asistente.ai.pricing import TokenUsage
from asistente.ai.usage import AiUsageService, UsageTotals
from asistente.users.models import User

TODAY = date(2026, 10, 5)
YESTERDAY = date(2026, 10, 4)


async def test_counts_text_and_voice_with_their_cost(session: AsyncSession, user: User) -> None:
    service = AiUsageService(session)

    await service.record(
        user, TODAY, model="gpt-6-luna", usage=TokenUsage(input_tokens=900, output_tokens=60)
    )
    await service.record_transcription(user, TODAY, model="gpt-4o-mini-transcribe", seconds=12)
    await service.record_transcription(user, YESTERDAY, model="gpt-4o-mini-transcribe", seconds=30)

    assert await service.totals(user, TODAY, TODAY) == UsageTotals(
        requests=1,
        input_tokens=900,
        output_tokens=60,
        transcriptions=1,
        audio_seconds=12,
        cost_micro_usd=120 + 600,
    )
    both_days = await service.totals(user, YESTERDAY, TODAY)
    assert (both_days.transcriptions, both_days.audio_seconds) == (2, 42)
    assert both_days.cost_micro_usd == 120 + 600 + 1_500


async def test_unknown_prices_count_usage_but_no_cost(session: AsyncSession, user: User) -> None:
    service = AiUsageService(session)

    await service.record_transcription(user, TODAY, model="otro-modelo", seconds=10)

    totals = await service.totals(user, TODAY, TODAY)
    assert (totals.transcriptions, totals.cost_micro_usd) == (1, 0)
