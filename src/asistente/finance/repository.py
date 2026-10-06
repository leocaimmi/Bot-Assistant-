"""Database queries of the finance module. Every query is scoped to a single user."""

from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from asistente.finance.models import (
    Account,
    Category,
    CategoryKeyword,
    Transaction,
    TransactionKind,
)
from asistente.finance.reports import TotalRow

# Any SELECT, whatever its columns (Select is variadic in SQLAlchemy 2.1).
SelectT = TypeVar("SelectT", bound=Select[*tuple[Any, ...]])


class FinanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def accounts(self, user_id: int) -> list[Account]:
        query = select(Account).where(Account.user_id == user_id).order_by(Account.id)
        return list(await self._session.scalars(query))

    async def account(self, user_id: int, account_id: int) -> Account | None:
        query = select(Account).where(Account.user_id == user_id, Account.id == account_id)
        return await self._session.scalar(query)

    async def categories(self, user_id: int, kind: TransactionKind | None = None) -> list[Category]:
        query = select(Category).where(Category.user_id == user_id)
        if kind is not None:
            query = query.where(Category.kind == kind)
        query = query.order_by(Category.kind, Category.is_fallback, Category.id)
        return list(await self._session.scalars(query))

    async def category(self, user_id: int, category_id: int) -> Category | None:
        query = select(Category).where(Category.user_id == user_id, Category.id == category_id)
        return await self._session.scalar(query)

    async def fallback_category(self, user_id: int, kind: TransactionKind) -> Category | None:
        query = (
            select(Category)
            .where(Category.user_id == user_id, Category.kind == kind, Category.is_fallback)
            .order_by(Category.id)
            .limit(1)
        )
        return await self._session.scalar(query)

    async def categories_by_keyword(self, user_id: int) -> dict[str, Category]:
        query = (
            select(CategoryKeyword.keyword, Category)
            .join(Category, CategoryKeyword.category_id == Category.id)
            .where(CategoryKeyword.user_id == user_id)
        )
        rows = await self._session.execute(query)
        return dict(rows.all())

    async def add_transaction(self, transaction: Transaction) -> Transaction:
        self._session.add(transaction)
        await self._session.flush()
        return transaction

    async def transaction(self, user_id: int, transaction_id: int) -> Transaction | None:
        query = _transactions_of(user_id).where(Transaction.id == transaction_id)
        return await self._session.scalar(query)

    async def transactions(
        self,
        user_id: int,
        *,
        limit: int,
        offset: int = 0,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Transaction]:
        query = (
            _in_period(_transactions_of(user_id), start, end)
            .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(await self._session.scalars(query))

    async def count_transactions(
        self, user_id: int, *, start: datetime | None = None, end: datetime | None = None
    ) -> int:
        query = select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
        return await self._session.scalar(_in_period(query, start, end)) or 0

    async def totals(self, user_id: int, *, start: datetime, end: datetime) -> list[TotalRow]:
        """Amounts summed per kind, category, account and description in ``[start, end)``."""
        group = (
            Transaction.kind,
            Transaction.category_id,
            Transaction.account_id,
            Transaction.description,
        )
        query = _in_period(
            select(*group, func.sum(Transaction.amount_cents), func.count(Transaction.id))
            .where(Transaction.user_id == user_id)
            .group_by(*group),
            start,
            end,
        )
        rows = await self._session.execute(query)
        return [
            TotalRow(kind, category_id, account_id, description, int(cents), count)
            for kind, category_id, account_id, description, cents, count in rows
        ]

    async def flush(self) -> None:
        await self._session.flush()

    async def delete_transaction(self, transaction: Transaction) -> None:
        await self._session.delete(transaction)
        await self._session.flush()


def _transactions_of(user_id: int) -> Select[Transaction]:
    return (
        select(Transaction)
        .options(joinedload(Transaction.account), joinedload(Transaction.category))
        .where(Transaction.user_id == user_id)
    )


def _in_period(query: SelectT, start: datetime | None, end: datetime | None) -> SelectT:
    if start is not None:
        query = query.where(Transaction.occurred_at >= start)
    if end is not None:
        query = query.where(Transaction.occurred_at < end)
    return query
