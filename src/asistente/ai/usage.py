"""How much the AI is used: a hard daily budget and per-day statistics."""

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.ai import pricing
from asistente.ai.models import AiUsage
from asistente.ai.pricing import TokenUsage
from asistente.core.errors import UserError
from asistente.users.models import User


class AiBudgetExceededError(UserError):
    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Llegaste al límite de {limit} consultas a la IA por hoy. "
            "Escribilo con el formato simple, por ejemplo <code>uber 2000</code>."
        )


class DailyBudget:
    """In-memory cap of AI requests per user and day.

    It is checked *before* calling the API and is not affected by database rollbacks,
    so a failing update can never be used to bypass it. It resets on restart, which only
    the allowed users can trigger; the provider's spending limit is the last safeguard.
    """

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._day: date | None = None
        self._used: Counter[int] = Counter()  # requests per Telegram user, for ``_day``

    def spend(self, telegram_id: int, today: date) -> None:
        """Count one request, or raise ``AiBudgetExceededError`` if none is left."""
        if today != self._day:
            self._day, self._used = today, Counter()
        if self._used[telegram_id] >= self.limit:
            raise AiBudgetExceededError(self.limit)
        self._used[telegram_id] += 1


@dataclass(frozen=True, slots=True)
class UsageTotals:
    requests: int  # text interpretations
    input_tokens: int
    output_tokens: int
    transcriptions: int
    audio_seconds: int
    cost_micro_usd: int

    @property
    def calls(self) -> int:
        """Every request to the AI, text or voice: what the daily budget counts."""
        return self.requests + self.transcriptions

    @property
    def cost_usd(self) -> Decimal:
        return Decimal(self.cost_micro_usd) / 1_000_000


class AiUsageService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, user: User, day: date, *, model: str, usage: TokenUsage) -> None:
        """Count one interpretation, priced with ``model``'s current price (nothing if unknown)."""
        row = await self._row(user, day)
        row.requests += 1
        row.input_tokens += usage.input_tokens
        row.output_tokens += usage.output_tokens
        row.cost_micro_usd += pricing.response_cost(model, usage) or 0
        await self._session.flush()

    async def record_transcription(
        self, user: User, day: date, *, model: str, seconds: int
    ) -> None:
        """Count one voice message of ``seconds``, priced like ``record``."""
        row = await self._row(user, day)
        row.transcriptions += 1
        row.audio_seconds += seconds
        row.cost_micro_usd += pricing.transcription_cost(model, seconds) or 0
        await self._session.flush()

    async def totals(self, user: User, start: date, end: date) -> UsageTotals:
        """Totals for days in ``[start, end]``."""
        row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(AiUsage.requests), 0),
                    func.coalesce(func.sum(AiUsage.input_tokens), 0),
                    func.coalesce(func.sum(AiUsage.output_tokens), 0),
                    func.coalesce(func.sum(AiUsage.transcriptions), 0),
                    func.coalesce(func.sum(AiUsage.audio_seconds), 0),
                    func.coalesce(func.sum(AiUsage.cost_micro_usd), 0),
                ).where(AiUsage.user_id == user.id, AiUsage.day >= start, AiUsage.day <= end)
            )
        ).one()
        return UsageTotals(*(int(value) for value in row))

    async def _row(self, user: User, day: date) -> AiUsage:
        row = await self._session.scalar(
            select(AiUsage).where(AiUsage.user_id == user.id, AiUsage.day == day)
        )
        if row is None:
            row = AiUsage(
                user_id=user.id,
                day=day,
                requests=0,
                input_tokens=0,
                output_tokens=0,
                transcriptions=0,
                audio_seconds=0,
                cost_micro_usd=0,
            )
            self._session.add(row)
        return row
