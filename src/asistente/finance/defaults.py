"""Initial categories, keywords and accounts for every user."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asistente.core.text import normalize
from asistente.finance.models import Account, Category, CategoryKeyword, TransactionKind
from asistente.users.models import User

EXPENSE = TransactionKind.EXPENSE
INCOME = TransactionKind.INCOME


@dataclass(frozen=True, slots=True)
class DefaultCategory:
    name: str
    emoji: str
    kind: TransactionKind
    keywords: tuple[str, ...] = ()
    is_fallback: bool = False


@dataclass(frozen=True, slots=True)
class DefaultAccount:
    name: str
    emoji: str
    aliases: tuple[str, ...]
    is_default: bool = False


DEFAULT_CATEGORIES = (
    DefaultCategory(
        "Transporte",
        "🚗",
        EXPENSE,
        (
            "sube",
            "uber",
            "didi",
            "cabify",
            "taxi",
            "remis",
            "colectivo",
            "bondi",
            "subte",
            "tren",
            "peaje",
            "estacionamiento",
            "nafta",
            "combustible",
            "gnc",
            "ypf",
            "shell",
            "axion",
        ),
    ),
    DefaultCategory(
        "Gimnasio", "🏋️", EXPENSE, ("gym", "gimnasio", "crossfit", "proteina", "creatina")
    ),
    DefaultCategory(
        "Supermercado",
        "🛒",
        EXPENSE,
        (
            "super",
            "supermercado",
            "coto",
            "carrefour",
            "jumbo",
            "disco",
            "chino",
            "almacen",
            "verduleria",
            "carniceria",
            "dietetica",
        ),
    ),
    DefaultCategory(
        "Comida",
        "🍔",
        EXPENSE,
        (
            "rappi",
            "pedidosya",
            "pedidos ya",
            "delivery",
            "resto",
            "restaurante",
            "desayuno",
            "almuerzo",
            "merienda",
            "cena",
            "cafe",
            "pizza",
            "empanadas",
            "hamburguesa",
            "helado",
        ),
    ),
    DefaultCategory(
        "Servicios",
        "💡",
        EXPENSE,
        (
            "luz",
            "gas",
            "internet",
            "wifi",
            "celular",
            "telefono",
            "edenor",
            "edesur",
            "metrogas",
            "aysa",
            "claro",
            "movistar",
            "telecentro",
            "abl",
        ),
    ),
    DefaultCategory(
        "Suscripciones",
        "📺",
        EXPENSE,
        ("netflix", "spotify", "disney", "hbo", "youtube", "prime", "icloud", "chatgpt"),
    ),
    DefaultCategory(
        "Salud",
        "💊",
        EXPENSE,
        ("farmacia", "medico", "dentista", "obra social", "prepaga", "remedios", "psicologo"),
    ),
    DefaultCategory(
        "Educación",
        "📚",
        EXPENSE,
        ("facultad", "curso", "libro", "libros", "apuntes", "fotocopias"),
    ),
    DefaultCategory(
        "Hogar", "🏠", EXPENSE, ("alquiler", "expensas", "limpieza", "ferreteria", "muebles")
    ),
    DefaultCategory(
        "Ropa", "👕", EXPENSE, ("ropa", "zapatillas", "remera", "pantalon", "campera", "buzo")
    ),
    DefaultCategory(
        "Salidas",
        "🎉",
        EXPENSE,
        ("salida", "boliche", "bar", "birra", "cerveza", "cine", "teatro", "recital"),
    ),
    DefaultCategory("Otros gastos", "📦", EXPENSE, is_fallback=True),
    DefaultCategory("Sueldo", "💼", INCOME, ("sueldo", "salario", "aguinaldo")),
    DefaultCategory("Transferencias", "🔁", INCOME, ("transferencia", "transf")),
    DefaultCategory("Freelance", "💻", INCOME, ("freelance",)),
    DefaultCategory(
        "Otros ingresos",
        "💰",
        INCOME,
        ("ingreso", "cobro", "cobre", "reintegro", "devolucion"),
        is_fallback=True,
    ),
)

DEFAULT_ACCOUNTS = (
    DefaultAccount("Mercado Pago", "📱", ("mp", "mercadopago", "mercado pago"), is_default=True),
    DefaultAccount("Efectivo", "💵", ("efectivo", "cash")),
    DefaultAccount("Banco", "🏦", ("banco", "debito")),
)


async def seed_defaults(session: AsyncSession, user: User) -> None:
    """Add the default categories, keywords and accounts the user is missing.

    Idempotent: never touches existing data, so it is safe to run on every startup and
    new defaults reach existing users. Keywords already used by the user are skipped.
    """
    category_names = set(
        await session.scalars(select(Category.name).where(Category.user_id == user.id))
    )
    keywords = set(
        await session.scalars(
            select(CategoryKeyword.keyword).where(CategoryKeyword.user_id == user.id)
        )
    )
    account_names = set(
        await session.scalars(select(Account.name).where(Account.user_id == user.id))
    )

    for default in DEFAULT_CATEGORIES:
        if default.name in category_names:
            continue
        category = Category(
            user_id=user.id,
            name=default.name,
            emoji=default.emoji,
            kind=default.kind,
            is_fallback=default.is_fallback,
            keywords=[],
        )
        for keyword in map(normalize, default.keywords):
            if keyword not in keywords:
                keywords.add(keyword)
                category.keywords.append(CategoryKeyword(user_id=user.id, keyword=keyword))
        session.add(category)

    has_default_account = bool(account_names)
    for default_account in DEFAULT_ACCOUNTS:
        if default_account.name in account_names:
            continue
        session.add(
            Account(
                user_id=user.id,
                name=default_account.name,
                emoji=default_account.emoji,
                aliases=[normalize(alias) for alias in default_account.aliases],
                is_default=default_account.is_default and not has_default_account,
            )
        )

    await session.flush()
