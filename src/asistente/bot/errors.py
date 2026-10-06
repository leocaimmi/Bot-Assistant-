import logging
from contextlib import suppress

from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)

ERROR_TEXT = "😵 Algo salió mal y no se guardó nada. Probá de nuevo en un rato."


async def on_error(event: ErrorEvent) -> bool:
    """Log unexpected errors and tell the user, without exposing internal details."""
    logger.error(
        "Unhandled error while processing update id=%s",
        event.update.update_id,
        exc_info=event.exception,
    )
    with suppress(TelegramAPIError):
        if event.update.callback_query is not None:
            await event.update.callback_query.answer(ERROR_TEXT, show_alert=True)
        elif event.update.message is not None:
            await event.update.message.answer(ERROR_TEXT)
    return True
