from datetime import date

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


def test_cost_estimate() -> None:
    totals = UsageTotals(requests=1000, input_tokens=1_000_000, output_tokens=100_000)

    assert totals.cost_usd("gpt-5.4-nano") == pytest.approx(0.20 + 0.125)
    assert totals.cost_usd("unknown-model") is None
