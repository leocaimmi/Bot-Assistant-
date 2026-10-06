from datetime import date
from decimal import Decimal

import pytest

from asistente.ai.usage import AiBudgetExceededError, DailyBudget, UsageTotals

TODAY = date(2026, 10, 5)


def test_budget_caps_requests_per_user_and_day() -> None:
    budget = DailyBudget(limit=2)

    budget.spend(111, TODAY)
    budget.spend(111, TODAY)
    budget.spend(222, TODAY)  # other users have their own count
    with pytest.raises(AiBudgetExceededError):
        budget.spend(111, TODAY)

    budget.spend(111, date(2026, 10, 6))  # a new day starts from zero


def test_zero_limit_disables_requests() -> None:
    with pytest.raises(AiBudgetExceededError):
        DailyBudget(limit=0).spend(111, TODAY)


def test_totals() -> None:
    totals = UsageTotals(
        requests=3,
        input_tokens=2_700,
        output_tokens=180,
        transcriptions=2,
        audio_seconds=20,
        cost_micro_usd=1_765,
    )

    assert totals.calls == 5
    assert totals.cost_usd == Decimal("0.001765")
