from asistente.finance.models import Account, Category, TransactionKind
from asistente.finance.reports import Detail, TotalRow, build_summary

EXPENSE = TransactionKind.EXPENSE
INCOME = TransactionKind.INCOME

CATEGORIES = {
    1: Category(id=1, name="Transporte", emoji="🚗", kind=EXPENSE),
    2: Category(id=2, name="Gimnasio", emoji="🏋️", kind=EXPENSE),
    3: Category(id=3, name="Transferencias", emoji="🔁", kind=INCOME),
}
ACCOUNTS = {
    10: Account(id=10, name="Mercado Pago", emoji="📱"),
    11: Account(id=11, name="Efectivo", emoji="💵"),
}


def _row(kind: TransactionKind, category: int, account: int, text: str, cents: int) -> TotalRow:
    return TotalRow(kind, category, account, text, cents, count=1)


def test_groups_expenses_by_category_and_income_by_account() -> None:
    rows = [
        _row(EXPENSE, 1, 10, "uber", 3_000_000),
        _row(EXPENSE, 1, 11, "sube", 1_500_000),
        _row(EXPENSE, 1, 10, "Uber", 500_000),
        _row(EXPENSE, 1, 10, "didi", 500_000),
        _row(EXPENSE, 1, 10, "remis", 100_000),
        _row(EXPENSE, 2, 10, "gym", 4_700_000),
        _row(INCOME, 3, 10, "transferencia utn", 20_000_000),
    ]

    summary = build_summary(2026, 10, rows, CATEGORIES, ACCOUNTS)

    assert [(g.name, g.cents) for g in summary.expenses] == [
        ("Transporte", 5_600_000),
        ("Gimnasio", 4_700_000),
    ]
    transport = summary.expenses[0]
    assert transport.details == (
        Detail("uber", 3_500_000),
        Detail("sube", 1_500_000),
        Detail("didi", 500_000),
    )
    assert transport.hidden == 1  # remis
    assert summary.expenses[1].hidden == 0
    assert [(g.name, g.cents) for g in summary.incomes] == [("Mercado Pago", 20_000_000)]
    assert summary.expense_total == 10_300_000
    assert summary.income_total == 20_000_000
    assert summary.balance == 9_700_000
    assert summary.transaction_count == 7


def test_empty_month() -> None:
    summary = build_summary(2026, 10, [], CATEGORIES, ACCOUNTS)

    assert summary.expenses == summary.incomes == ()
    assert summary.balance == 0
    assert summary.transaction_count == 0


def test_blank_descriptions_get_a_label() -> None:
    summary = build_summary(2026, 10, [_row(EXPENSE, 2, 10, "", 100)], CATEGORIES, ACCOUNTS)

    assert summary.expenses[0].details == (Detail("sin descripción", 100),)
