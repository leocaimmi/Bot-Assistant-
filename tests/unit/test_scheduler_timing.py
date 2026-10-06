from datetime import UTC, datetime

import pytest

from asistente.bot.scheduler import seconds_until_next_round


def _at(minute: int, second: int, microsecond: int = 0) -> datetime:
    return datetime(2026, 10, 6, 12, minute, second, microsecond, tzinfo=UTC)


@pytest.mark.parametrize(
    ("now", "wait"),
    [
        (_at(0, 0, 500_000), 0.5),  # right at startup: this minute's round
        (_at(0, 1, 5_000), 59.995),  # just after a round: the next minute
        (_at(0, 30), 31),
        (_at(0, 59, 999_000), 1.001),
    ],
)
def test_rounds_run_just_after_each_minute(now: datetime, wait: float) -> None:
    assert seconds_until_next_round(now) == pytest.approx(wait, abs=1e-3)


def test_never_waits_zero_or_more_than_a_minute() -> None:
    for second in range(60):
        assert 0 < seconds_until_next_round(_at(5, second)) <= 60


def test_no_wait_when_disabled() -> None:
    assert seconds_until_next_round(_at(0, 30), every=0) == 0
