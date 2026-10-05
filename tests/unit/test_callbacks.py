import pytest
from aiogram.filters.callback_data import CallbackData

from asistente.bot.handlers.finance.callbacks import (
    SummaryCallback,
    TxAction,
    TxCallback,
    TxPageCallback,
)


@pytest.mark.parametrize(
    ("callback_type", "data"),
    [
        (SummaryCallback, "sum:2026:13"),
        (SummaryCallback, "sum:1999:12"),
        (TxPageCallback, "txp:-1:0:0"),
        (TxPageCallback, "txp:0:2026:0"),
        (TxPageCallback, "txp:0:1500:3"),
        (TxCallback, "tx:open:0"),
        (TxCallback, "tx:hack:1"),
    ],
)
def test_rejects_forged_data(callback_type: type[CallbackData], data: str) -> None:
    # pydantic and aiogram both raise ValueError subclasses.
    with pytest.raises(ValueError):
        callback_type.unpack(data)


def test_round_trip() -> None:
    page = TxPageCallback(page=2, year=2026, month=9)

    assert TxPageCallback.unpack(page.pack()).period == (2026, 9)
    assert TxPageCallback.unpack(TxPageCallback(page=0).pack()).period is None
    assert TxCallback.unpack("tx:del:7") == TxCallback(action=TxAction.DELETE, tx_id=7)
