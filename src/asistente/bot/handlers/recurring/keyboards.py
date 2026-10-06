from collections.abc import Sequence

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from asistente.bot.handlers.recurring.callbacks import RecurringCallback
from asistente.finance.models import RecurringPayment


def listed(payments: Sequence[RecurringPayment]) -> InlineKeyboardMarkup | None:
    if not payments:
        return None
    builder = InlineKeyboardBuilder()
    for number, payment in enumerate(payments, start=1):
        builder.button(text=f"🗑 {number}", callback_data=RecurringCallback(payment_id=payment.id))
    builder.adjust(5)
    return builder.as_markup()
