"""Categories and keywords: list them, teach new keywords, create categories."""

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from asistente.bot.handlers.finance import views
from asistente.bot.ui import split_message
from asistente.finance.categories import CategoryService
from asistente.users.models import User


async def list_categories(message: Message, category_service: CategoryService, user: User) -> None:
    overview = views.categories_overview(await category_service.overview(user))
    for part in split_message(overview):
        await message.answer(part)


async def assign_keyword(
    message: Message, command: CommandObject, category_service: CategoryService, user: User
) -> None:
    if not command.args:
        await message.answer(views.KEYWORD_USAGE)
        return
    assignment = await category_service.assign_keyword(user, command.args)
    await message.answer(views.keyword_assigned(assignment))


async def create_category(
    message: Message, command: CommandObject, category_service: CategoryService, user: User
) -> None:
    if not command.args:
        await message.answer(views.NEW_CATEGORY_USAGE)
        return
    category = await category_service.create(user, command.args)
    await message.answer(views.category_created(category))


def build_router() -> Router:
    router = Router(name="finance.categories")
    router.message.register(list_categories, Command("categorias"))
    router.message.register(assign_keyword, Command("palabra"))
    router.message.register(create_category, Command("nueva_categoria"))
    return router
