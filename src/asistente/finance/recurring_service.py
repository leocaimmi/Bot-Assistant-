"""Installments and fixed payments: registering them, and charging them every month.

Each charge is a normal transaction, created when it is due ("zapatillas (2/9)"), so
monthly summaries and lists show it like any other movement. Charging and moving on to
the next month happen in the same database transaction: a charge is never made twice.
"""

from dataclasses import dataclass, replace
from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from asistente.core.errors import UserError
from asistente.core.schedule import Repeat, Schedule, next_occurrence
from asistente.finance.models import Category, RecurringPayment, Transaction, installment_label
from asistente.finance.parser import parse_entry
from asistente.finance.recurring import RecurringRequest
from asistente.finance.service import FinanceService
from asistente.users.models import User

CHARGE_TIME = time(9, 0)  # automatic charges are registered at 9:00, local time
MAX_ACTIVE_RECURRING = 30
MAX_CATCH_UP = 12  # charges per payment and round when the bot was off for months
DUE_BATCH = 50


class TooManyRecurringError(UserError):
    def __init__(self) -> None:
        super().__init__(
            f"Ya tenés {MAX_ACTIVE_RECURRING} cuotas y gastos fijos: da de baja alguno en /fijos."
        )


class RecurringNotFoundError(UserError):
    def __init__(self) -> None:
        super().__init__("Ese pago ya no existe.")


class InstallmentTooSmallError(UserError):
    def __init__(self) -> None:
        super().__init__("🤔 El total no alcanza para dividirlo en esas cuotas.")


@dataclass(frozen=True, slots=True)
class RegisteredRecurring:
    transaction: Transaction | None  # the charge registered right now, if any
    payment: RecurringPayment | None  # what is still to come; None after the last installment


@dataclass(frozen=True, slots=True)
class Charged:
    payment: RecurringPayment
    transactions: list[Transaction]
    chat_id: int  # private chats: the user's Telegram id


class RecurringPaymentService:
    def __init__(self, session: AsyncSession, tz: ZoneInfo) -> None:
        self._session = session
        self._tz = tz
        self._finance = FinanceService(session, tz)

    async def register(
        self, user: User, request: RecurringRequest, *, now: datetime
    ) -> RegisteredRecurring:
        """Register today's charge (if it is due today) and what is still to come.

        Raises ``MissingAmountError`` when the text has no amount.
        """
        local_now = now.astimezone(self._tz)
        entry = parse_entry(request.text, today=local_now.date())
        total = request.installments
        each = first = entry.amount_cents
        if total is not None and request.split_total:
            each, remainder = divmod(entry.amount_cents, total)
            if each <= 0:
                raise InstallmentTooSmallError
            first = each + remainder  # the cents that do not divide evenly go first

        last_one_now = total is not None and request.number == total
        if not last_one_now and await self._count_active(user) >= MAX_ACTIVE_RECURRING:
            raise TooManyRecurringError

        prepared = await self._finance.prepare_entry(
            user, replace(entry, amount_cents=first), now=now
        )
        description = prepared.description
        # "zapatillas 10.000 cuota 1 de 9 ayer": the purchase day sets the monthly day.
        paid_on = entry.day or local_now.date()
        starts_now = request.day_of_month in (None, local_now.day)
        transaction = None
        if starts_now:
            prepared.description = installment_label(description, request.number, total)
            transaction = await self._finance.save(prepared)
        if last_one_now:
            return RegisteredRecurring(transaction, None)

        day = request.day_of_month or paid_on.day
        schedule = Schedule(Repeat.MONTHLY, CHARGE_TIME, day_of_month=day)
        # After the charge just registered, the next one is the following month. If that
        # date already passed (a purchase from long ago), the scheduler catches up.
        after = datetime.combine(paid_on, time.max, tzinfo=self._tz) if starts_now else local_now
        next_run = next_occurrence(schedule, after)
        if next_run is None:  # pragma: no cover - monthly schedules always run again
            return RegisteredRecurring(transaction, None)
        payment = RecurringPayment(
            user_id=user.id,
            account=prepared.account,
            category=prepared.category,
            description=description,
            amount_cents=each,
            day_of_month=day,
            installments=total,
            next_number=request.number + 1 if starts_now else request.number,
            next_run_at=next_run,
            active=True,
        )
        self._session.add(payment)
        await self._session.flush()
        return RegisteredRecurring(transaction, payment)

    async def active(self, user: User) -> list[RecurringPayment]:
        """Payments still to come, the next one first."""
        query = (
            select(RecurringPayment)
            .options(
                selectinload(RecurringPayment.account), selectinload(RecurringPayment.category)
            )
            .where(RecurringPayment.user_id == user.id, RecurringPayment.active.is_(True))
            .order_by(RecurringPayment.next_run_at, RecurringPayment.id)
        )
        return list(await self._session.scalars(query))

    async def cancel(self, user: User, payment_id: int) -> None:
        """Stop future charges; what was already registered stays."""
        payment = await self._session.scalar(
            select(RecurringPayment).where(
                RecurringPayment.id == payment_id,
                RecurringPayment.user_id == user.id,
                RecurringPayment.active.is_(True),
            )
        )
        if payment is None:
            raise RecurringNotFoundError
        payment.active = False
        await self._session.flush()

    async def due_ids(self, now: datetime, *, limit: int = DUE_BATCH) -> list[int]:
        """Payments of every user that are due, the oldest first."""
        query = (
            select(RecurringPayment.id)
            .where(RecurringPayment.active.is_(True), RecurringPayment.next_run_at <= now)
            .order_by(RecurringPayment.next_run_at)
            .limit(limit)
        )
        return list(await self._session.scalars(query))

    async def charge(self, payment_id: int, now: datetime) -> Charged | None:
        """Register every charge of the payment due by ``now`` (at most ``MAX_CATCH_UP``)."""
        row = (
            await self._session.execute(
                select(RecurringPayment, User.telegram_id)
                .join(User, User.id == RecurringPayment.user_id)
                .where(
                    RecurringPayment.id == payment_id,
                    RecurringPayment.active.is_(True),
                    RecurringPayment.next_run_at <= now,
                )
            )
        ).one_or_none()
        if row is None:  # cancelled or charged in the meantime
            return None
        payment, chat_id = row
        category = await self._session.get(Category, payment.category_id)
        if category is None:  # pragma: no cover - the foreign key forbids it
            return None

        schedule = Schedule(Repeat.MONTHLY, CHARGE_TIME, day_of_month=payment.day_of_month)
        created: list[Transaction] = []
        for _ in range(MAX_CATCH_UP):
            if not payment.active or payment.next_run_at > now:
                break
            created.append(
                Transaction(
                    user_id=payment.user_id,
                    account_id=payment.account_id,
                    category_id=payment.category_id,
                    kind=category.kind,
                    amount_cents=payment.amount_cents,
                    description=payment.label(payment.next_number),
                    occurred_at=payment.next_run_at,
                )
            )
            if payment.installments is not None and payment.next_number >= payment.installments:
                payment.active = False  # that was the last installment
                break
            payment.next_number += 1
            next_run = next_occurrence(schedule, payment.next_run_at.astimezone(self._tz))
            if next_run is None:  # pragma: no cover - monthly schedules always run again
                payment.active = False
                break
            payment.next_run_at = next_run
        self._session.add_all(created)
        await self._session.flush()
        return Charged(payment, created, chat_id)

    async def turn_off(self, payment_id: int) -> None:
        """Stop a payment that cannot be charged (used by the scheduler, not by users)."""
        payment = await self._session.get(RecurringPayment, payment_id)
        if payment is not None:
            payment.active = False
            await self._session.flush()

    async def _count_active(self, user: User) -> int:
        query = (
            select(func.count())
            .select_from(RecurringPayment)
            .where(RecurringPayment.user_id == user.id, RecurringPayment.active.is_(True))
        )
        return await self._session.scalar(query) or 0


def last_charge_at(payment: RecurringPayment, tz: ZoneInfo) -> datetime | None:
    """When the last installment will be registered; ``None`` for a fixed payment."""
    if payment.installments is None:
        return None
    schedule = Schedule(Repeat.MONTHLY, CHARGE_TIME, day_of_month=payment.day_of_month)
    run = payment.next_run_at.astimezone(tz)
    for _ in range(payment.installments - payment.next_number):  # at most MAX_INSTALLMENTS
        following = next_occurrence(schedule, run)
        if following is None:  # pragma: no cover - monthly schedules always run again
            break
        run = following
    return run
