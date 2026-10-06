"""Texts for installments and fixed payments (HTML, Argentine dates). Descriptions are escaped."""

from collections.abc import Sequence
from datetime import date
from html import escape
from zoneinfo import ZoneInfo

from asistente.core.money import format_ars
from asistente.finance.models import RecurringPayment, TransactionKind
from asistente.finance.recurring_service import Charged, RegisteredRecurring, last_charge_at

EMPTY_LIST = (
    "🔁 No tenés cuotas ni gastos fijos.\n"
    "Por ejemplo: <code>zapatillas 10.000 cuota 1 de 9</code> o "
    "<code>seguro del celu 5.000 todos los meses</code>"
)
LAST_INSTALLMENT = "🎉 Era la última cuota."


def created(registered: RegisteredRecurring, tz: ZoneInfo, *, today: date) -> str:
    payment = registered.payment
    if payment is None:
        return LAST_INSTALLMENT
    next_day = payment.next_run_at.astimezone(tz).date()
    header = f"🔁 <b>{_kind(payment)}: {_name(payment)}</b> · {format_ars(payment.amount_cents)}"
    if payment.installments is None:
        when = (
            f"Te lo anoto el {payment.day_of_month} de cada mes (próximo: {_day(next_day, today)})."
        )
        return f"{header}\n{when}\nLo ves en /fijos."
    total = payment.installments
    last = last_charge_at(payment, tz)
    end = f" ({_day(last.date(), today)})" if last is not None else ""
    return (
        f"{header}\n"
        f"Te anoto la {payment.next_number}/{total} el {_day(next_day, today)} y sigo cada mes "
        f"hasta la {total}/{total}{end}.\nLas ves en /fijos."
    )


def payment_list(payments: Sequence[RecurringPayment], tz: ZoneInfo, *, today: date) -> str:
    if not payments:
        return EMPTY_LIST
    lines = ["🔁 <b>Cuotas y gastos fijos</b>", ""]
    for number, payment in enumerate(payments, start=1):
        next_day = _day(payment.next_run_at.astimezone(tz).date(), today)
        if payment.installments is None:
            when = f"el {payment.day_of_month} de cada mes · próximo {next_day}"
        else:
            last = last_charge_at(payment, tz)
            end = f" · última {_day(last.date(), today)}" if last is not None else ""
            when = f"cuota {payment.next_number}/{payment.installments} el {next_day}{end}"
        lines += [
            f"{number}. <b>{_name(payment)}</b> · {format_ars(payment.amount_cents)}",
            f"    {when}",
        ]
    lines += ["", "Tocá 🗑 para dar de baja uno (lo ya anotado queda)."]
    return "\n".join(lines)


def charged(result: Charged, tz: ZoneInfo) -> str:
    """The notice sent after registering a charge by itself."""
    lines = [
        f"🔁 Anoté <b>{escape(transaction.description)}</b>: "
        f"{format_ars(transaction.amount_cents)} "
        f"({transaction.occurred_at.astimezone(tz):%d/%m})"
        for transaction in result.transactions
    ]
    if result.payment.installments is not None and not result.payment.active:
        lines.append(LAST_INSTALLMENT)
    return "\n".join(lines)


def _kind(payment: RecurringPayment) -> str:
    if payment.installments is not None:
        return "Cuotas"
    return "Ingreso fijo" if payment.category.kind is TransactionKind.INCOME else "Gasto fijo"


def _name(payment: RecurringPayment) -> str:
    name = payment.description or payment.category.name
    return escape(name[:1].upper() + name[1:])


def _day(day: date, today: date) -> str:
    return f"{day:%d/%m}" if day.year == today.year else f"{day:%d/%m/%Y}"
