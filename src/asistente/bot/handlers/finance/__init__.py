from aiogram import Router

from asistente.bot.handlers.finance import categories, reports, transactions


def build_router() -> Router:
    """Finance commands and buttons. Plain-text entries are handled by ``free_text``."""
    router = Router(name="finance")
    router.include_routers(
        transactions.build_router(),
        reports.build_router(),
        categories.build_router(),
    )
    return router
