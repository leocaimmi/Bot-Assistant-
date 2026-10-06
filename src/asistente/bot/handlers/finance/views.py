"""Texts shown to the user (HTML). Every user-provided value is escaped."""

from html import escape
from zoneinfo import ZoneInfo

from asistente.core.dates import format_datetime, format_short_datetime, month_label
from asistente.core.money import format_ars
from asistente.finance.categories import KeywordAssignment
from asistente.finance.models import Category, Transaction, TransactionKind
from asistente.finance.reports import Group, MonthlySummary
from asistente.finance.service import (
    AccountChange,
    AmountChange,
    CategoryChange,
    Change,
    DayChange,
    DescriptionChange,
    TransactionPage,
)

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


def change_field(transaction: Transaction, change: Change, tz: ZoneInfo) -> tuple[str, str]:
    """Label and current value (HTML-escaped) of the field that ``change`` touches."""
    match change:
        case AmountChange():
            return "Importe", format_ars(transaction.amount_cents)
        case CategoryChange():
            return "Categoría", escape(transaction.category.label)
        case DayChange(at=None):
            return "Fecha", f"{transaction.occurred_at.astimezone(tz):%d/%m/%Y}"
        case DayChange():
            return "Fecha", f"{transaction.occurred_at.astimezone(tz):%d/%m/%Y %H:%M}"
        case DescriptionChange():
            return "Descripción", escape(transaction.description or "-")
        case AccountChange():
            account = transaction.account
            return "Cuenta", f"{account.emoji} {escape(account.name)}"


def change_preview(transaction: Transaction, changes: list[Change], tz: ZoneInfo) -> str:
    """``"Importe: $2.000 → $2.500"`` lines for changes not applied yet."""
    lines = []
    for change in changes:
        label, before = change_field(transaction, change, tz)
        lines.append(f"{label}: {before} → {_new_value(change, tz)}")
    return "\n".join(lines)


def _new_value(change: Change, tz: ZoneInfo) -> str:
    match change:
        case AmountChange(cents):
            return format_ars(cents)
        case CategoryChange(category):
            return escape(category.label)
        case DayChange(day, None):
            return f"{day:%d/%m/%Y}"
        case DayChange(day, at):
            return f"{day:%d/%m/%Y} {at:%H:%M}"
        case DescriptionChange(description):
            return escape(description)
        case AccountChange(account):
            return f"{account.emoji} {escape(account.name)}"


def deleted(transaction_id: int) -> str:
    return f"🗑 Movimiento <i>#{transaction_id}</i> borrado."


def monthly_summary(summary: MonthlySummary) -> str:
    lines = [f"📊 <b>Resumen de {month_label(summary.year, summary.month)}</b>"]
    if not summary.transaction_count:
        lines += ["", "No hay movimientos en este mes."]
        return "\n".join(lines)

    if summary.expenses:
        lines += ["", f"💸 <b>Gastaste {format_ars(summary.expense_total)}</b>"]
        lines += _group_lines(summary.expenses, total=summary.expense_total)
    if summary.incomes:
        lines += ["", f"💰 <b>Ingresaste {format_ars(summary.income_total)}</b>"]
        lines += _group_lines(summary.incomes, total=None)

    plural = "movimiento" if summary.transaction_count == 1 else "movimientos"
    lines += [
        "",
        f"⚖️ Balance: <b>{format_ars(summary.balance, signed=True)}</b>",
        f"🧾 {summary.transaction_count} {plural}",
    ]
    return "\n".join(lines)


def _group_lines(groups: tuple[Group, ...], *, total: int | None) -> list[str]:
    lines = []
    for group in groups:
        share = f" ({_percentage(group.cents, total)})" if total else ""
        lines.append(f"{group.emoji} {escape(group.name)}: <b>{format_ars(group.cents)}</b>{share}")
        details = " · ".join(
            f"{escape(detail.label)} {format_ars(detail.cents)}" for detail in group.details
        )
        lines.append(f"    └ {details}")
    return lines


def categories_overview(categories: list[Category]) -> str:
    lines = ["🏷 <b>Categorías y palabras clave</b>"]
    for kind, title in ((TransactionKind.EXPENSE, "Gastos"), (TransactionKind.INCOME, "Ingresos")):
        lines += ["", f"<b>{title}</b>"]
        for category in (c for c in categories if c.kind is kind):
            keywords = ", ".join(escape(keyword.keyword) for keyword in category.keywords)
            if category.is_fallback:
                keywords = (
                    f"{keywords}; además, todo lo que no coincide"
                    if keywords
                    else ("todo lo que no coincide con otra")
                )
            lines.append(f"{category.emoji} <b>{escape(category.name)}</b>: {keywords or '-'}")
    lines += [
        "",
        "Enseñame una palabra: <code>/palabra nafta transporte</code>",
        "Creá una categoría: <code>/nueva_categoria 🚙 Auto</code>",
    ]
    return "\n".join(lines)


def keyword_assigned(assignment: KeywordAssignment) -> str:
    keyword = f"<b>{escape(assignment.keyword)}</b>"
    target = escape(assignment.category.label)
    if assignment.previous is not None and assignment.previous.id == assignment.category.id:
        return f"👌 {keyword} ya estaba en {target}."
    moved = (
        f" (antes estaba en {escape(assignment.previous.label)})"
        if assignment.previous is not None
        else ""
    )
    return (
        f"✅ Listo: {keyword} → {target}{moved}.\n"
        "Los movimientos nuevos que la usen van a esa categoría; los anteriores no cambian."
    )


def category_created(category: Category) -> str:
    kind = KIND_LABELS[category.kind].lower()
    example = escape(category.name.lower())
    return (
        f"✅ Categoría de {kind} {escape(category.label)} creada.\n"
        f"Enseñale palabras con <code>/palabra &lt;palabra&gt; {example}</code>."
    )


KEYWORD_USAGE = (
    "Escribí la palabra y la categoría, por ejemplo:\n"
    "<code>/palabra nafta transporte</code>\n"
    "<code>/palabra pedidos ya comida</code>\n"
    "Mirá las categorías con /categorias."
)
NEW_CATEGORY_USAGE = (
    "Escribí el nombre, opcionalmente con un emoji, por ejemplo:\n"
    "<code>/nueva_categoria 🚙 Auto</code>\n"
    "<code>/nueva_categoria ingreso 🎓 Becas</code>"
)


def _percentage(part: int, total: int) -> str:
    percentage = round(part * 100 / total)
    return "<1%" if percentage == 0 else f"{percentage}%"


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
INVALID_SUMMARY_MONTH = (
    "🤔 No entendí el mes. Probá con <code>/resumen</code>, <code>/resumen septiembre</code> "
    "o <code>/resumen 09/2026</code>."
)
