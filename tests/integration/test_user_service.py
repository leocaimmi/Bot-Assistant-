from sqlalchemy.ext.asyncio import AsyncSession

from asistente.users.service import UserService


async def test_get_or_create_registers_once(session: AsyncSession) -> None:
    service = UserService(session)

    user, created = await service.get_or_create(telegram_id=111)
    same_user, created_again = await service.get_or_create(telegram_id=111)

    assert created is True
    assert created_again is False
    assert same_user.id == user.id
