"""Monthly summary: totals per category (expenses) and per account (income)."""

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from asistente.core.text import normalize
from asistente.finance.models import Account, Category, TransactionKind

MAX_DETAILS = 3
NO_DESCRIPTION = "sin descripción"


@dataclass(frozen=True, slots=True)
class TotalRow:
    """Sum of the transactions sharing kind, category, account and description."""

    kind: TransactionKind
    category_id: int
    account_id: int
    description: str
    cents: int
    count: int


@dataclass(frozen=True, slots=True)
class Detail:
    label: str
    cents: int


@dataclass(frozen=True, slots=True)
class Group:
    emoji: str
    name: str
    cents: int
    details: tuple[Detail, ...]  # the biggest ones
    hidden: int = 0  # how many other descriptions are not listed


@dataclass(frozen=True, slots=True)
class MonthlySummary:
    year: int
    month: int
    expenses: tuple[Group, ...]  # by category, biggest first
    incomes: tuple[Group, ...]  # by account, biggest first
    transaction_count: int

    @property
    def expense_total(self) -> int:
        return sum(group.cents for group in self.expenses)

    @property
    def income_total(self) -> int:
        return sum(group.cents for group in self.incomes)

    @property
    def balance(self) -> int:
        return self.income_total - self.expense_total


def build_summary(
    year: int,
    month: int,
    rows: Iterable[TotalRow],
    categories: Mapping[int, Category],
    accounts: Mapping[int, Account],
) -> MonthlySummary:
    rows = list(rows)
    expenses = _groups(
        (row for row in rows if row.kind is TransactionKind.EXPENSE),
        key=lambda row: row.category_id,
        header=lambda key: (categories[key].emoji, categories[key].name),
    )
    incomes = _groups(
        (row for row in rows if row.kind is TransactionKind.INCOME),
        key=lambda row: row.account_id,
        header=lambda key: (accounts[key].emoji, accounts[key].name),
    )
    return MonthlySummary(
        year=year,
        month=month,
        expenses=expenses,
        incomes=incomes,
        transaction_count=sum(row.count for row in rows),
    )


def _groups(
    rows: Iterable[TotalRow],
    *,
    key: Callable[[TotalRow], int],
    header: Callable[[int], tuple[str, str]],
) -> tuple[Group, ...]:
    totals: Counter[int] = Counter()
    # Descriptions are merged in normalized form: "Uber", "uber" and "UBER" add up together.
    details: defaultdict[int, Counter[str]] = defaultdict(Counter)
    labels: dict[str, str] = {}
    for row in rows:
        group_key = key(row)
        detail_key = normalize(row.description)
        totals[group_key] += row.cents
        details[group_key][detail_key] += row.cents
        labels.setdefault(detail_key, row.description.strip() or NO_DESCRIPTION)

    groups = []
    for group_key, cents in totals.most_common():
        emoji, name = header(group_key)
        top_details = tuple(
            Detail(labels[detail_key], detail_cents)
            for detail_key, detail_cents in details[group_key].most_common(MAX_DETAILS)
        )
        hidden = len(details[group_key]) - len(top_details)
        groups.append(Group(emoji, name, cents, top_details, hidden))
    return tuple(groups)
