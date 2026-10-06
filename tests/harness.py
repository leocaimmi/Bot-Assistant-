"""In-memory Telegram harness: feeds fake updates to the dispatcher and records bot calls."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from itertools import count
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageReplyMarkup,
    EditMessageText,
    SendMessage,
    TelegramMethod,
)
from aiogram.methods.base import TelegramType
from aiogram.types import CallbackQuery, Chat, InlineKeyboardMarkup, Message, Update, User

from asistente.bot.errors import ERROR_TEXT
from tests.factories import ALLOWED_USER_ID, TEST_BOT_TOKEN


class RecordingSession(BaseSession):
    """Bot session that records API calls instead of reaching Telegram."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []
        self._message_ids = count(1000)

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,  # noqa: ASYNC109 (signature defined by aiogram)
    ) -> TelegramType:
        self.requests.append(method)
        return self._fake_result(method)  # type: ignore[no-any-return]

    def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError("the harness does not download files")

    def _fake_result(self, method: TelegramMethod[Any]) -> Any:
        if isinstance(method, SendMessage | EditMessageText):
            message_id = getattr(method, "message_id", None) or next(self._message_ids)
            return Message(
                message_id=message_id,
                date=datetime.now(UTC),
                chat=Chat(id=int(method.chat_id or 0), type="private"),
                text=method.text,
            )
        return True


class BotHarness:
    """Talks to the dispatcher like a Telegram user would."""

    def __init__(self, dispatcher: Dispatcher, *, user_id: int = ALLOWED_USER_ID) -> None:
        self.dispatcher = dispatcher
        self.user_id = user_id
        self.session = RecordingSession()
        self.bot = Bot(
            TEST_BOT_TOKEN,
            session=self.session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self._update_ids = count(1)

    async def send(
        self, text: str, *, user_id: int | None = None, chat_type: str = "private"
    ) -> None:
        sender_id = user_id or self.user_id
        update_id = next(self._update_ids)
        chat_id = sender_id if chat_type == "private" else -sender_id
        message = Message(
            message_id=update_id,
            date=datetime.now(UTC),
            chat=Chat(id=chat_id, type=chat_type),
            from_user=self._user(sender_id),
            text=text,
        )
        await self._feed(Update(update_id=update_id, message=message))

    async def click(self, callback_data: str, *, message_id: int = 1) -> None:
        update_id = next(self._update_ids)
        callback = CallbackQuery(
            id=str(update_id),
            from_user=self._user(self.user_id),
            chat_instance="test",
            data=callback_data,
            message=Message(
                message_id=message_id,
                date=datetime.now(UTC),
                chat=Chat(id=self.user_id, type="private"),
                text="previous message",
            ),
        )
        await self._feed(Update(update_id=update_id, callback_query=callback))

    @property
    def replies(self) -> list[str]:
        """Texts sent or edited by the bot, oldest first."""
        return [
            request.text or ""
            for request in self.session.requests
            if isinstance(request, SendMessage | EditMessageText)
        ]

    @property
    def last_reply(self) -> str:
        assert self.replies, "the bot did not reply"
        return self.replies[-1]

    @property
    def alerts(self) -> list[str]:
        return [
            request.text or ""
            for request in self.session.requests
            if isinstance(request, AnswerCallbackQuery)
        ]

    def last_keyboard(self) -> InlineKeyboardMarkup:
        """Most recent inline keyboard sent or edited by the bot."""
        for request in reversed(self.session.requests):
            if isinstance(request, SendMessage | EditMessageText | EditMessageReplyMarkup):
                markup = request.reply_markup
                if isinstance(markup, InlineKeyboardMarkup):
                    return markup
        raise AssertionError("the bot did not send any keyboard")

    def button(self, label_part: str) -> str:
        """Callback data of the first button in the last keyboard whose label contains text."""
        for row in self.last_keyboard().inline_keyboard:
            for button in row:
                if label_part in button.text and button.callback_data is not None:
                    return button.callback_data
        raise AssertionError(f"no button containing {label_part!r}")

    async def _feed(self, update: Update) -> None:
        sent_before = len(self.session.requests)
        await self.dispatcher.feed_update(self.bot, update)
        new_requests = self.session.requests[sent_before:]
        errors = [r for r in new_requests if ERROR_TEXT in (getattr(r, "text", None) or "")]
        assert not errors, "a handler raised an exception (see the captured log)"

    @staticmethod
    def _user(user_id: int) -> User:
        return User(id=user_id, is_bot=False, first_name="Leo")
