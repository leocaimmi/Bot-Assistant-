from collections.abc import Sequence

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from asistente.bot.handlers.common import examples_keyboard
from asistente.bot.handlers.recurring.callbacks import RecurringCallback
from asistente.bot.help import HelpTopic
from asistente.finance.models import RecurringPayment


def listed(payments: Sequence[RecurringPayment]) -> InlineKeyboardMarkup:
    if not payments:
        return examples_keyboard(HelpTopic.RECURRING)
    builder = InlineKeyboardBuilder()
    for number, payment in enumerate(payments, start=1):
        builder.button(text=f"🗑 {number}", callback_data=RecurringCallback(payment_id=payment.id))
    builder.adjust(5)
    return builder.as_markup()
