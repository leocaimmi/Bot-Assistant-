"""How much the AI is used: a hard daily budget and per-day statistics."""

from collections import Counter
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.ai.models import AiUsage
from asistente.core.errors import UserError
from asistente.users.models import User

# Price per million tokens (input, output) in USD, to estimate the cost in /ia.
PRICES_PER_MILLION = {"gpt-5.4-nano": (0.20, 1.25)}


class AiBudgetExceededError(UserError):
    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Llegaste al límite de {limit} interpretaciones con IA por hoy. "
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
    requests: int
    input_tokens: int
    output_tokens: int

    def cost_usd(self, model: str) -> float | None:
        prices = PRICES_PER_MILLION.get(model)
        if prices is None:
            return None
        input_price, output_price = prices
        return (self.input_tokens * input_price + self.output_tokens * output_price) / 1_000_000


class AiUsageService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, user: User, day: date, *, input_tokens: int, output_tokens: int) -> None:
        usage = await self._session.scalar(
            select(AiUsage).where(AiUsage.user_id == user.id, AiUsage.day == day)
        )
        if usage is None:
            usage = AiUsage(user_id=user.id, day=day, requests=0, input_tokens=0, output_tokens=0)
            self._session.add(usage)
        usage.requests += 1
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        await self._session.flush()

    async def totals(self, user: User, start: date, end: date) -> UsageTotals:
        """Totals for days in ``[start, end]``."""
        row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(AiUsage.requests), 0),
                    func.coalesce(func.sum(AiUsage.input_tokens), 0),
                    func.coalesce(func.sum(AiUsage.output_tokens), 0),
                ).where(AiUsage.user_id == user.id, AiUsage.day >= start, AiUsage.day <= end)
            )
        ).one()
        requests, input_tokens, output_tokens = (int(value) for value in row)
        return UsageTotals(requests, input_tokens, output_tokens)
