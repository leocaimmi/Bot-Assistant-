"""Texts shown to the user (HTML). Every user-provided value is escaped."""

from html import escape
from zoneinfo import ZoneInfo

from asistente.core.dates import format_datetime, format_short_datetime, month_label
from asistente.core.money import format_ars
from asistente.finance.models import Transaction, TransactionKind
from asistente.finance.service import TransactionPage

KIND_LABELS = {TransactionKind.EXPENSE: "Gasto", TransactionKind.INCOME: "Ingreso"}
KIND_EMOJIS = {TransactionKind.EXPENSE: "💸", TransactionKind.INCOME: "💰"}


def registered_title(transaction: Transaction) -> str:
    return f"✅ {KIND_LABELS[transaction.kind]} registrado"


def transaction_card(transaction: Transaction, tz: ZoneInfo, *, title: str | None = None) -> str:
    category = transaction.category
    account = transaction.account
    detail = f" · {escape(transaction.description)}" if transaction.description else ""
    lines = [
        f"{KIND_EMOJIS[transaction.kind]} <b>{format_ars(transaction.amount_cents)}</b>"
        f" · {KIND_LABELS[transaction.kind]}",
        f"{category.emoji} {escape(category.name)}{detail}",
        f"{account.emoji} {escape(account.name)}",
        f"📅 {format_datetime(transaction.occurred_at, tz)}",
        f"<i>#{transaction.id}</i>",
    ]
    if title:
        lines[:0] = [f"<b>{title}</b>", ""]
    return "\n".join(lines)


def transaction_line(transaction: Transaction, tz: ZoneInfo) -> str:
    label = transaction.description or transaction.category.name
    amount = format_ars(transaction.signed_cents, signed=True)
    return (
        f"<code>#{transaction.id}</code> {format_short_datetime(transaction.occurred_at, tz)}"
        f" {transaction.category.emoji} {escape(label)} <b>{amount}</b>"
    )


def transactions_page(page: TransactionPage, tz: ZoneInfo, month: tuple[int, int] | None) -> str:
    title = (
        f"🧾 <b>Movimientos de {month_label(*month)}</b>"
        if month
        else "🧾 <b>Últimos movimientos</b>"
    )
    if page.total == 0:
        return f"{title}\n\nNo hay movimientos todavía."
    lines = [
        title,
        f"Página {page.number + 1} de {page.count} · {page.total} en total",
        "",
        *(transaction_line(transaction, tz) for transaction in page.items),
        "",
        "Tocá un número para verlo o editarlo.",
    ]
    return "\n".join(lines)


def deleted(transaction_id: int) -> str:
    return f"🗑 Movimiento <i>#{transaction_id}</i> borrado."


ASK_AMOUNT = "💲 Mandame el nuevo importe, por ejemplo <code>2.500</code>.\n/cancelar para dejarlo."
ASK_DESCRIPTION = "📝 Mandame la nueva descripción.\n/cancelar para dejarla."
ASK_DAY = (
    "📅 ¿Qué día fue? Por ejemplo <code>hoy</code>, <code>ayer</code> o <code>15/09</code>.\n"
    "/cancelar para dejarlo."
)
INVALID_AMOUNT = "🤔 No entendí el importe. Probá con algo como <code>2.500</code> o /cancelar."
INVALID_DAY = (
    "🤔 No entendí la fecha. Probá con <code>ayer</code> o <code>15/09</code>, o /cancelar."
)
EMPTY_DESCRIPTION = "La descripción no puede estar vacía. Probá de nuevo o /cancelar."
INVALID_MONTH = (
    "🤔 No entendí el mes. Probá con <code>/movimientos septiembre</code> "
    "o <code>/movimientos 09/2026</code>."
)
