"""Changes waiting for the user's OK, kept on the server until a button applies them.

The change is stored in the FSM data; its buttons only carry a random token, so an old
or forged button cannot apply anything. Each key holds one pending change at a time.
"""

import secrets
from typing import Annotated, Any

from aiogram.fsm.context import FSMContext
from pydantic import Field

Token = Annotated[str, Field(pattern=r"^[0-9a-f]{8}$")]


async def keep(state: FSMContext, key: str, change: dict[str, Any]) -> str:
    """Store ``change`` under ``key``, replacing the previous one; return its token."""
    token = secrets.token_hex(4)
    await state.update_data({key: {**change, "token": token}})
    return token


async def take(state: FSMContext, key: str, token: str) -> dict[str, Any] | None:
    """The change of ``token``, removed so it is applied at most once; ``None`` if stale."""
    pending = (await state.get_data()).get(key)
    await state.update_data({key: None})
    if not pending or pending.get("token") != token:
        return None
    return dict(pending)
