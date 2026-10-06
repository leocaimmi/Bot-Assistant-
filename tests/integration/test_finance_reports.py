from datetime import UTC, datetime

from asistente.finance.service import FinanceService
from asistente.users.models import User

OCTOBER = datetime(2026, 10, 5, 17, 30, tzinfo=UTC)


async def test_monthly_summary_uses_local_month_boundaries(
    finance: FinanceService, user: User
) -> None:
    await finance.register(user, "uber 2000", now=OCTOBER)
    await finance.register(user, "gym 47.000", now=OCTOBER)
    await finance.register(user, "transferencia utn 200.000", now=OCTOBER)
    # 01/10 02:00 UTC is still September in Buenos Aires.
    await finance.register(user, "sube 1500", now=datetime(2026, 10, 1, 2, 0, tzinfo=UTC))

    october = await finance.monthly_summary(user, 2026, 10)
    september = await finance.monthly_summary(user, 2026, 9)

    assert [(g.name, g.cents) for g in october.expenses] == [
        ("Gimnasio", 4_700_000),
        ("Transporte", 200_000),
    ]
    assert [(g.name, g.cents) for g in october.incomes] == [("Mercado Pago", 20_000_000)]
    assert october.balance == 20_000_000 - 4_900_000
    assert [(g.name, g.cents) for g in september.expenses] == [("Transporte", 150_000)]
    assert september.incomes == ()
