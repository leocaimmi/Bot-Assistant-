"""Business rules for transactions. Every operation is scoped to the given user."""

from dataclasses import dataclass
from datetime import date, datetime
from math import ceil
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from asistente.core.dates import at_local_time, month_range
from asistente.core.errors import UserError
from asistente.core.money import MAX_AMOUNT_CENTS
from asistente.finance.matching import find_phrase
from asistente.finance.models import (
    MAX_DESCRIPTION_LENGTH,
    Account,
    Category,
    Transaction,
    TransactionKind,
)
from asistente.finance.parser import parse_entry
from asistente.finance.reports import MonthlySummary, build_summary
from asistente.finance.repository import FinanceRepository
from asistente.users.models import User

PAGE_SIZE = 10


class TransactionNotFoundError(UserError):
    def __init__(self) -> None:
        super().__init__("Ese movimiento ya no existe.")


class CategoryNotFoundError(UserError):
    def __init__(self) -> None:
        super().__init__("Esa categoría ya no existe.")


class AccountNotFoundError(UserError):
    def __init__(self) -> None:
        super().__init__("Esa cuenta ya no existe.")


class InvalidAmountError(UserError):
    def __init__(self) -> None:
        super().__init__("El importe tiene que ser mayor a cero.")


class FinanceNotReadyError(RuntimeError):
    """The user has no accounts or fallback categories (defaults were not seeded)."""


@dataclass(frozen=True, slots=True)
class TransactionPage:
    items: list[Transaction]
    number: int  # zero-based
    total: int
    size: int = PAGE_SIZE

    @property
    def count(self) -> int:
        return max(1, ceil(self.total / self.size))

    @property
    def has_previous(self) -> bool:
        return self.number > 0

    @property
    def has_next(self) -> bool:
        return self.number + 1 < self.count


class FinanceService:
    def __init__(self, session: AsyncSession, tz: ZoneInfo) -> None:
        self._repository = FinanceRepository(session)
        self._tz = tz

    async def register(self, user: User, text: str, *, now: datetime) -> Transaction:
        """Create a transaction from a message such as ``"uber 2000"``.

        Raises ``MissingAmountError`` when the text has no amount.
        """
        local_now = now.astimezone(self._tz)
        entry = parse_entry(text, today=local_now.date())
        words = list(entry.words)

        account = await self._take_account(user, words)
        category = await self._match_category(user, words, entry.kind)
        occurred_at = (
            now
            if entry.day is None or entry.day == local_now.date()
            else at_local_time(entry.day, local_now.time(), self._tz)
        )
        transaction = Transaction(
            user_id=user.id,
            account=account,
            category=category,
            kind=category.kind,
            amount_cents=entry.amount_cents,
            description=_clean_description(" ".join(words)),
            occurred_at=occurred_at,
        )
        return await self._repository.add_transaction(transaction)

    async def get(self, user: User, transaction_id: int) -> Transaction:
        transaction = await self._repository.transaction(user.id, transaction_id)
        if transaction is None:
            raise TransactionNotFoundError
        return transaction

    async def page(
        self, user: User, number: int, *, month: tuple[int, int] | None = None
    ) -> TransactionPage:
        start, end = month_range(*month, self._tz) if month else (None, None)
        total = await self._repository.count_transactions(user.id, start=start, end=end)
        number = min(max(number, 0), max(0, ceil(total / PAGE_SIZE) - 1))
        items = await self._repository.transactions(
            user.id, limit=PAGE_SIZE, offset=number * PAGE_SIZE, start=start, end=end
        )
        return TransactionPage(items=items, number=number, total=total)

    async def monthly_summary(self, user: User, year: int, month: int) -> MonthlySummary:
        start, end = month_range(year, month, self._tz)
        rows = await self._repository.totals(user.id, start=start, end=end)
        categories = {category.id: category for category in await self.categories(user)}
        accounts = {account.id: account for account in await self.accounts(user)}
        return build_summary(year, month, rows, categories, accounts)

    async def categories(self, user: User, kind: TransactionKind | None = None) -> list[Category]:
        return await self._repository.categories(user.id, kind)

    async def accounts(self, user: User) -> list[Account]:
        return await self._repository.accounts(user.id)

    async def change_amount(self, user: User, transaction_id: int, cents: int) -> Transaction:
        if not 0 < cents <= MAX_AMOUNT_CENTS:
            raise InvalidAmountError
        transaction = await self.get(user, transaction_id)
        transaction.amount_cents = cents
        await self._repository.flush()
        return transaction

    async def change_description(
        self, user: User, transaction_id: int, description: str
    ) -> Transaction:
        transaction = await self.get(user, transaction_id)
        transaction.description = _clean_description(description)
        await self._repository.flush()
        return transaction

    async def change_day(self, user: User, transaction_id: int, day: date) -> Transaction:
        """Move the transaction to another day, keeping its time of day."""
        transaction = await self.get(user, transaction_id)
        local_time = transaction.occurred_at.astimezone(self._tz).time()
        transaction.occurred_at = at_local_time(day, local_time, self._tz)
        await self._repository.flush()
        return transaction

    async def change_category(
        self, user: User, transaction_id: int, category_id: int
    ) -> Transaction:
        transaction = await self.get(user, transaction_id)
        category = await self._repository.category(user.id, category_id)
        if category is None:
            raise CategoryNotFoundError
        transaction.category = category
        transaction.kind = category.kind
        await self._repository.flush()
        return transaction

    async def change_account(self, user: User, transaction_id: int, account_id: int) -> Transaction:
        transaction = await self.get(user, transaction_id)
        account = await self._repository.account(user.id, account_id)
        if account is None:
            raise AccountNotFoundError
        transaction.account = account
        await self._repository.flush()
        return transaction

    async def toggle_kind(self, user: User, transaction_id: int) -> Transaction:
        """Turn an expense into an income or vice versa, re-matching its category."""
        transaction = await self.get(user, transaction_id)
        kind = (
            TransactionKind.INCOME
            if transaction.kind is TransactionKind.EXPENSE
            else TransactionKind.EXPENSE
        )
        transaction.category = await self._match_category(
            user, transaction.description.split(), kind
        )
        transaction.kind = kind
        await self._repository.flush()
        return transaction

    async def delete(self, user: User, transaction_id: int) -> None:
        transaction = await self.get(user, transaction_id)
        await self._repository.delete_transaction(transaction)

    async def _take_account(self, user: User, words: list[str]) -> Account:
        """Account named in the message (its words are removed) or the default one."""
        accounts = await self._repository.accounts(user.id)
        if not accounts:
            raise FinanceNotReadyError(f"user {user.id} has no accounts")
        aliases = {alias: account for account in accounts for alias in account.aliases}
        match = find_phrase(words, aliases)
        if match is not None:
            del words[match.start : match.end]
            return match.value
        return next((account for account in accounts if account.is_default), accounts[0])

    async def _match_category(
        self, user: User, words: list[str], kind: TransactionKind | None
    ) -> Category:
        """Category of the first keyword found; the fallback one when nothing matches."""
        by_keyword = await self._repository.categories_by_keyword(user.id)
        if kind is not None:
            by_keyword = {word: cat for word, cat in by_keyword.items() if cat.kind is kind}
        match = find_phrase(words, by_keyword)
        if match is not None:
            return match.value

        fallback_kind = kind or TransactionKind.EXPENSE
        fallback = await self._repository.fallback_category(user.id, fallback_kind)
        if fallback is None:
            raise FinanceNotReadyError(f"user {user.id} has no {fallback_kind} fallback")
        return fallback


def _clean_description(text: str) -> str:
    return " ".join(text.split())[:MAX_DESCRIPTION_LENGTH]
