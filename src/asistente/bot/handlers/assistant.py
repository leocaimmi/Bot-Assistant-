"""Messages the rules do not understand, interpreted by the AI with one request each.

Nothing the AI says is trusted blindly: values are validated (``ai.validation``), deletes
always ask for confirmation and edits show a before/after preview first. The pending
edit is kept server-side; its button only carries a random token.
"""

import secrets
from datetime import date
from html import escape
from typing import Annotated, Any

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pydantic import Field

from asistente.ai import validation
from asistente.ai.interpreter import (
    MAX_MESSAGE_LENGTH,
    Interpreter,
    InterpreterContext,
    InterpreterError,
)
from asistente.ai.schema import Changes, Intent, Interpretation, Target
from asistente.ai.usage import AiUsageService, DailyBudget
from asistente.bot.handlers import gym as gym_handlers
from asistente.bot.handlers.finance import entries as finance_entries
from asistente.bot.handlers.finance import keyboards, views
from asistente.bot.ui import edit_or_send
from asistente.config import Settings
from asistente.core.errors import UserError
from asistente.core.text import normalize
from asistente.finance.service import (
    AmountChange,
    CategoryChange,
    Change,
    DayChange,
    DescriptionChange,
    FinanceService,
)
from asistente.gym.service import GymService
from asistente.users.models import User

AI_UNAVAILABLE = (
    "😵 No pude consultar a la IA ahora. Probá con el formato simple, "
    "por ejemplo <code>uber 2000</code>."
)
AI_DISABLED = (
    "🤖 La IA está desactivada: falta configurar <code>OPENAI_API_KEY</code>. "
    "El bot funciona igual con el formato simple."
)
PENDING_EDIT_KEY = "ai_pending_edit"


class AiEditCallback(CallbackData, prefix="aie"):
    apply: bool
    token: Annotated[str, Field(pattern=r"^[0-9a-f]{8}$")]


async def interpret(
    message: Message,
    text: str,
    *,
    interpreter: Interpreter,
    budget: DailyBudget,
    finance: FinanceService,
    gym: GymService,
    ai_usage: AiUsageService,
    user: User,
    settings: Settings,
    state: FSMContext,
) -> bool:
    """Ask the AI and act on its answer. ``False`` means "not understood"."""
    if len(text) > MAX_MESSAGE_LENGTH:
        return False
    today = message.date.astimezone(settings.tz).date()
    budget.spend(user.telegram_id, today)  # before the request: nothing bypasses the cap

    context = InterpreterContext(
        categories=[category.name for category in await finance.categories(user)],
        exercises=[f"{e.name} ({e.muscle_group.value})" for e in await gym.exercises(user)],
    )
    try:
        result = await interpreter.interpret(text, context, user_key=str(user.telegram_id))
    except InterpreterError:
        await message.answer(AI_UNAVAILABLE)
        return True
    await ai_usage.record(
        user,
        today,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
    )

    try:
        return await _act(
            message, text, result.interpretation, today, finance, gym, user, settings, state
        )
    except UserError as error:
        # Answer here instead of raising, so the usage record above is kept.
        await message.answer(str(error))
        return True


async def _act(
    message: Message,
    text: str,
    interpretation: Interpretation,
    today: date,
    finance: FinanceService,
    gym: GymService,
    user: User,
    settings: Settings,
    state: FSMContext,
) -> bool:
    tz = settings.tz
    match interpretation.intent:
        case Intent.REGISTER:
            movements = interpretation.movements[: validation.MAX_MOVEMENTS]
            entries = [validation.to_entry(movement, text, today) for movement in movements]
            valid = [entry for entry in entries if entry is not None]
            if not valid or len(valid) != len(entries):
                return False  # one invalid value invalidates the whole answer
            for entry in valid:
                transaction = await finance.register_entry(user, entry, now=message.date)
                await finance_entries.answer_registered(message, transaction, tz)
            return True

        case Intent.DELETE:
            transaction = await finance.find(
                user,
                validation.to_target(interpretation.target, text, today),
                shown_as=_target_text(interpretation.target),
            )
            await message.answer(
                views.transaction_card(transaction, tz, title="¿Borrar este movimiento?"),
                reply_markup=keyboards.delete_confirmation(transaction.id),
            )
            return True

        case Intent.EDIT:
            transaction = await finance.find(
                user,
                validation.to_target(interpretation.target, text, today),
                shown_as=_target_text(interpretation.target),
            )
            changes = await _changes(interpretation.changes, text, today, finance, user)
            if changes is None:
                return False
            if not changes:
                await message.answer(
                    views.transaction_card(transaction, tz, title="✏️ ¿Qué querés cambiar?"),
                    reply_markup=keyboards.transaction_editor(transaction),
                )
                return True
            token = secrets.token_hex(4)
            await state.update_data({PENDING_EDIT_KEY: _pending(token, transaction.id, changes)})
            preview = views.change_preview(transaction, changes, tz)
            await message.answer(
                views.transaction_card(transaction, tz, title=f"✏️ ¿Aplico este cambio?\n{preview}"),
                reply_markup=_confirm_keyboard(token),
            )
            return True

        case Intent.WORKOUT:
            items = validation.to_exercise_items(interpretation.exercises, text)
            if items is None:
                return False
            day = validation.safe_day(interpretation.workout_day, today) or today
            logged = await gym.log(user, items, day=day)
            await gym_handlers.answer_logged(message, logged, today)
            return True

        case Intent.UNKNOWN:
            return False


async def _changes(
    changes: Changes | None, text: str, today: date, finance: FinanceService, user: User
) -> list[Change] | None:
    """Validated changes, ``[]`` when none were asked, ``None`` if any value is invalid."""
    if changes is None:
        return []
    result: list[Change] = []
    if changes.amount is not None:
        cents = validation.safe_amount(changes.amount, text)
        if cents is None:
            return None
        result.append(AmountChange(cents))
    if changes.category is not None:
        by_name = {
            normalize(category.name): category for category in await finance.categories(user)
        }
        category = by_name.get(normalize(changes.category))
        if category is None:
            return None
        result.append(CategoryChange(category))
    if changes.day is not None:
        day = validation.safe_day(changes.day, today)
        if day is None:
            return None
        result.append(DayChange(day))
    if changes.description is not None and changes.description.strip():
        result.append(DescriptionChange(" ".join(changes.description.split())))
    return result


def _pending(token: str, transaction_id: int, changes: list[Change]) -> dict[str, Any]:
    pending: dict[str, Any] = {"token": token, "tx_id": transaction_id}
    for change in changes:
        match change:
            case AmountChange(cents):
                pending["amount_cents"] = cents
            case CategoryChange(category):
                pending["category_id"] = category.id
            case DayChange(day):
                pending["day"] = day.isoformat()
            case DescriptionChange(description):
                pending["description"] = description
    return pending


def _confirm_keyboard(token: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Aplicar", callback_data=AiEditCallback(apply=True, token=token))
    builder.button(text="✖️ Cancelar", callback_data=AiEditCallback(apply=False, token=token))
    return builder.as_markup()


def _target_text(target: Target | None) -> str:
    if target is None:
        return ""
    return " ".join(part for part in (target.description, target.amount, target.day) if part)


async def resolve_edit(
    callback: CallbackQuery,
    callback_data: AiEditCallback,
    state: FSMContext,
    bot: Bot,
    finance: FinanceService,
    user: User,
    settings: Settings,
) -> None:
    data = await state.get_data()
    pending = data.get(PENDING_EDIT_KEY)
    await state.update_data({PENDING_EDIT_KEY: None})
    if not pending or pending.get("token") != callback_data.token:
        await callback.answer("Este cambio ya no está disponible.", show_alert=True)
        return
    if not callback_data.apply:
        await edit_or_send(callback, bot, "👌 Cambio descartado.", None)
        await callback.answer()
        return

    transaction_id = int(pending["tx_id"])
    if "amount_cents" in pending:
        await finance.change_amount(user, transaction_id, int(pending["amount_cents"]))
    if "category_id" in pending:
        await finance.change_category(user, transaction_id, int(pending["category_id"]))
    if "day" in pending:
        await finance.change_day(user, transaction_id, date.fromisoformat(pending["day"]))
    if "description" in pending:
        await finance.change_description(user, transaction_id, str(pending["description"]))

    transaction = await finance.get(user, transaction_id)
    await edit_or_send(
        callback,
        bot,
        views.transaction_card(transaction, settings.tz, title="✏️ Movimiento actualizado"),
        keyboards.transaction_actions(transaction_id),
    )
    await callback.answer("Cambios aplicados")


async def show_usage(
    message: Message,
    ai_usage: AiUsageService,
    user: User,
    settings: Settings,
    interpreter: Interpreter | None = None,
) -> None:
    if interpreter is None:
        await message.answer(AI_DISABLED)
        return
    today = message.date.astimezone(settings.tz).date()
    today_totals = await ai_usage.totals(user, today, today)
    month = await ai_usage.totals(user, today.replace(day=1), today)
    lines = [
        f"🤖 <b>Uso de IA</b> ({escape(settings.openai_model)})",
        f"Hoy: {today_totals.requests} de {settings.ai_daily_limit} consultas",
        f"Este mes: {month.requests} consultas · {_thousands(month.input_tokens)} tokens de "
        f"entrada · {_thousands(month.output_tokens)} de salida",
    ]
    if (cost := month.cost_usd(settings.openai_model)) is not None:
        lines.append(f"Costo estimado del mes: US$ {cost:.4f}".replace(".", ","))
    await message.answer("\n".join(lines))


def _thousands(number: int) -> str:
    return f"{number:,}".replace(",", ".")


def build_router() -> Router:
    router = Router(name="assistant")
    router.message.register(show_usage, Command("ia"))
    router.callback_query.register(resolve_edit, AiEditCallback.filter())
    return router
