from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.users.models import User
from tests.factories import STRANGER_USER_ID
from tests.harness import BotHarness


async def test_start_greets_and_registers_user(harness: BotHarness, session: AsyncSession) -> None:
    await harness.send("/start")

    assert "¡Hola, Leo!" in harness.last_reply
    assert "/ayuda" in harness.last_reply
    assert await session.scalar(select(func.count()).select_from(User)) == 1


async def test_ignores_unauthorized_users_silently(
    harness: BotHarness, session: AsyncSession
) -> None:
    await harness.send("/start", user_id=STRANGER_USER_ID)

    assert harness.session.requests == []
    assert await session.scalar(select(func.count()).select_from(User)) == 0


async def test_ignores_group_chats(harness: BotHarness) -> None:
    await harness.send("/start", chat_type="group")

    assert harness.session.requests == []


async def test_unknown_command_points_to_help(harness: BotHarness) -> None:
    await harness.send("/inexistente")

    assert "/ayuda" in harness.last_reply


async def test_cancel_without_pending_action(harness: BotHarness) -> None:
    await harness.send("/cancelar")

    assert harness.last_reply == "No había nada para cancelar."
