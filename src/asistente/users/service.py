from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.users.models import User


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, telegram_id: int) -> tuple[User, bool]:
        """Return the user for ``telegram_id`` and whether it was just created."""
        user = await self._session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is not None:
            return user, False

        user = User(telegram_id=telegram_id)
        self._session.add(user)
        await self._session.flush()
        return user, True
