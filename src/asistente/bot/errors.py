import logging
from contextlib import suppress

from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

from asistente.core.errors import UserError

logger = logging.getLogger(__name__)

ERROR_TEXT = "😵 Algo salió mal y no se guardó nada. Probá de nuevo en un rato."


async def on_error(event: ErrorEvent) -> bool:
    """Tell the user what happened without exposing internal details.

    ``UserError`` messages are meant for the user; anything else is logged as a bug.
    The transaction of the update was already rolled back by ``DbSessionMiddleware``.
    """
    if isinstance(event.exception, UserError):
        await _notify(event, str(event.exception))
        return True

    logger.error(
        "Unhandled error while processing update id=%s",
        event.update.update_id,
        exc_info=event.exception,
    )
    await _notify(event, ERROR_TEXT)
    return True


async def _notify(event: ErrorEvent, text: str) -> None:
    with suppress(TelegramAPIError):
        if event.update.callback_query is not None:
            await event.update.callback_query.answer(text, show_alert=True)
        elif event.update.message is not None:
            await event.update.message.answer(text)
