from aiogram import Router

from asistente.bot.handlers.finance import categories, entries, reports, transactions


def build_router() -> Router:
    router = Router(name="finance")
    # Commands and buttons first; free text ("uber 2000") is the catch-all of the module.
    router.include_routers(
        transactions.build_router(),
        reports.build_router(),
        categories.build_router(),
        entries.build_router(),
    )
    return router
