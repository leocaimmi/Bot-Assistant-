"""Voice messages: one speech-to-text request, then the same path as a typed message.

The bot first shows what it heard, so a wrong transcription is obvious, and then the
transcript goes through the free rules (and the AI only if they do not understand it).
The audio is downloaded to memory, sent only to OpenAI and never stored.
"""

import io
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from asistente.ai.interpreter import Interpreter
from asistente.ai.transcriber import Transcriber, TranscriberError, clean_transcript
from asistente.ai.usage import AiUsageService, DailyBudget
from asistente.bot.handlers import free_text
from asistente.config import Settings
from asistente.core.errors import UserError
from asistente.finance.recurring_service import RecurringPaymentService
from asistente.finance.service import FinanceService
from asistente.gym.service import GymService
from asistente.reminders.service import ReminderService
from asistente.users.models import User

# Enough to dictate a whole workout, and a cap on what one message can cost.
MAX_VOICE_SECONDS = 60
# A minute of Telegram voice (Opus) is about 250 KB: anything much bigger is not one.
MAX_VOICE_BYTES = 1_000_000

VOICE_DISABLED = (
    "🎙 Para entender audios necesito la IA: falta configurar <code>OPENAI_API_KEY</code>. "
    "Mientras tanto, escribime el mensaje."
)
VOICE_TOO_LONG = "🎙 Mandame audios de hasta un minuto (podés separarlo en partes)."
VOICE_EMPTY = "🎙 No escuché nada en el audio. Probá de nuevo."
VOICE_FAILED = "😵 No pude escuchar el audio ahora. Probá de nuevo o escribilo."


async def handle_voice(
    message: Message,
    bot: Bot,
    finance: FinanceService,
    gym: GymService,
    ai_usage: AiUsageService,
    reminders: ReminderService,
    recurring: RecurringPaymentService,
    user: User,
    settings: Settings,
    state: FSMContext,
    ai_budget: DailyBudget,
    interpreter: Interpreter | None = None,
    transcriber: Transcriber | None = None,
) -> None:
    voice = message.voice
    if voice is None:  # guaranteed by the filter
        return
    if transcriber is None:
        await message.answer(VOICE_DISABLED)
        return
    if voice.duration > MAX_VOICE_SECONDS or (voice.file_size or 0) > MAX_VOICE_BYTES:
        await message.answer(VOICE_TOO_LONG)
        return

    today = message.date.astimezone(settings.tz).date()
    ai_budget.spend(user.telegram_id, today)  # before downloading: nothing bypasses the cap
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    audio = io.BytesIO()
    await bot.download(voice, destination=audio)
    try:
        heard = await transcriber.transcribe(audio.getvalue())
    except TranscriberError:
        await message.answer(VOICE_FAILED)
        return
    await ai_usage.record_transcription(
        user, today, model=settings.openai_transcription_model, seconds=voice.duration
    )

    text = clean_transcript(heard)
    if not text:
        await message.answer(VOICE_EMPTY)
        return
    await message.answer(f"🎙 <i>{escape(heard)}</i>")
    try:
        await free_text.route_text(
            message,
            text,
            finance=finance,
            gym=gym,
            reminders=reminders,
            recurring=recurring,
            ai_usage=ai_usage,
            user=user,
            settings=settings,
            state=state,
            ai_budget=ai_budget,
            interpreter=interpreter,
        )
    except UserError as error:
        # Answer here instead of raising, so the usage record above is kept.
        await message.answer(str(error))


def build_router() -> Router:
    router = Router(name="voice")
    router.message.register(handle_voice, StateFilter(None), F.voice)
    return router
