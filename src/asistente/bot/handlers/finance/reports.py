"""Monthly summary: how much went where, and how much came in."""

from datetime import datetime

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from asistente.bot.handlers.finance import keyboards, views
from asistente.bot.handlers.finance.callbacks import SummaryCallback
from asistente.bot.ui import edit_or_send
from asistente.config import Settings
from asistente.core.dates import parse_month
from asistente.finance.service import FinanceService
from asistente.users.models import User


async def show_summary(
    message: Message,
    command: CommandObject,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    today = message.date.astimezone(settings.tz).date()
    current = (today.year, today.month)
    month = parse_month(command.args, today) if command.args else current
    if month is None:
        await message.answer(views.INVALID_SUMMARY_MONTH)
        return

    summary = await finance.monthly_summary(user, *month)
    await message.answer(
        views.monthly_summary(summary),
        reply_markup=keyboards.summary_navigation(summary, current),
    )


async def change_summary_month(
    callback: CallbackQuery,
    callback_data: SummaryCallback,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    now = datetime.now(settings.tz)
    summary = await finance.monthly_summary(user, callback_data.year, callback_data.month)
    await edit_or_send(
        callback,
        bot,
        views.monthly_summary(summary),
        keyboards.summary_navigation(summary, (now.year, now.month)),
    )
    await callback.answer()


def build_router() -> Router:
    router = Router(name="finance.reports")
    router.message.register(show_summary, Command("resumen"))
    router.callback_query.register(change_summary_month, SummaryCallback.filter())
    return router
