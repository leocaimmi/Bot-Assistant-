"""Managing categories and the keywords that select them."""

from dataclasses import dataclass
from html import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from asistente.core.errors import UserError
from asistente.core.text import normalize
from asistente.finance.matching import MAX_PHRASE_TOKENS
from asistente.finance.models import Account, Category, CategoryKeyword, TransactionKind
from asistente.users.models import User

MAX_KEYWORD_LENGTH = 40
MAX_CATEGORY_NAME_LENGTH = 40
MAX_EMOJI_LENGTH = 8
DEFAULT_EMOJI = "🏷️"

_KIND_WORDS = {
    "gasto": TransactionKind.EXPENSE,
    "gastos": TransactionKind.EXPENSE,
    "ingreso": TransactionKind.INCOME,
    "ingresos": TransactionKind.INCOME,
}


class UnknownCategoryError(UserError):
    def __init__(self) -> None:
        super().__init__(
            "🤔 No encontré esa categoría. Escribí la palabra y después la categoría, "
            "por ejemplo <code>/palabra nafta transporte</code>. Mirá /categorias."
        )


class InvalidKeywordError(UserError):
    def __init__(self) -> None:
        super().__init__(
            f"La palabra clave puede tener hasta {MAX_PHRASE_TOKENS} palabras "
            f"y {MAX_KEYWORD_LENGTH} letras."
        )


class KeywordIsAccountAliasError(UserError):
    def __init__(self, keyword: str, account: str) -> None:
        super().__init__(f"«{escape(keyword)}» ya sirve para elegir la cuenta {escape(account)}.")


class InvalidCategoryNameError(UserError):
    def __init__(self) -> None:
        super().__init__(
            f"El nombre tiene que tener letras o números y hasta {MAX_CATEGORY_NAME_LENGTH} "
            "caracteres, por ejemplo <code>/nueva_categoria 🚙 Auto</code>."
        )


class CategoryAlreadyExistsError(UserError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Ya existe la categoría {escape(name)}.")


@dataclass(frozen=True, slots=True)
class KeywordAssignment:
    keyword: str
    category: Category
    previous: Category | None  # where the keyword was before, if it moved


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def overview(self, user: User) -> list[Category]:
        """Every category of the user with its keywords loaded."""
        query = (
            select(Category)
            .options(selectinload(Category.keywords))
            .where(Category.user_id == user.id)
            .order_by(Category.kind, Category.is_fallback, Category.id)
        )
        return list(await self._session.scalars(query))

    async def assign_keyword(self, user: User, text: str) -> KeywordAssignment:
        """``"nafta auto"``: make the keyword "nafta" select the category "Auto".

        The category is the longest trailing part of the text that names one, so names
        with spaces work too: ``"cafe otros gastos"``.
        """
        words = normalize(text).split()
        categories = {normalize(category.name): category for category in await self._all(user)}
        for split in range(1, len(words)):
            category = categories.get(" ".join(words[split:]))
            if category is not None:
                return await self._assign(user, " ".join(words[:split]), category)
        raise UnknownCategoryError

    async def create(self, user: User, text: str) -> Category:
        """``"🚙 Auto"`` creates an expense category; ``"ingreso Becas"`` an income one."""
        tokens = text.split()
        kind = TransactionKind.EXPENSE
        if tokens and normalize(tokens[0]) in _KIND_WORDS:
            kind = _KIND_WORDS[normalize(tokens.pop(0))]
        emoji = DEFAULT_EMOJI
        if tokens and _is_emoji(tokens[0]):
            emoji = tokens.pop(0)

        name = " ".join(tokens)
        if not normalize(name) or len(name) > MAX_CATEGORY_NAME_LENGTH:
            raise InvalidCategoryNameError
        name = name[0].upper() + name[1:]
        existing = {normalize(category.name): category for category in await self._all(user)}
        if normalize(name) in existing:
            raise CategoryAlreadyExistsError(existing[normalize(name)].label)

        category = Category(
            user_id=user.id, name=name, emoji=emoji, kind=kind, is_fallback=False, keywords=[]
        )
        self._session.add(category)
        await self._session.flush()
        return category

    async def _assign(self, user: User, keyword: str, category: Category) -> KeywordAssignment:
        if len(keyword.split()) > MAX_PHRASE_TOKENS or len(keyword) > MAX_KEYWORD_LENGTH:
            raise InvalidKeywordError
        await self._ensure_not_account_alias(user, keyword)

        existing = await self._session.scalar(
            select(CategoryKeyword)
            .options(joinedload(CategoryKeyword.category))
            .where(CategoryKeyword.user_id == user.id, CategoryKeyword.keyword == keyword)
        )
        previous = None
        if existing is None:
            self._session.add(
                CategoryKeyword(user_id=user.id, category_id=category.id, keyword=keyword)
            )
        else:
            previous = existing.category
            existing.category = category
        await self._session.flush()
        return KeywordAssignment(keyword=keyword, category=category, previous=previous)

    async def _ensure_not_account_alias(self, user: User, keyword: str) -> None:
        # Account words are removed before matching categories, so they could never match.
        accounts = await self._session.scalars(select(Account).where(Account.user_id == user.id))
        for account in accounts:
            if keyword in account.aliases:
                raise KeywordIsAccountAliasError(keyword, account.name)

    async def _all(self, user: User) -> list[Category]:
        query = select(Category).where(Category.user_id == user.id)
        return list(await self._session.scalars(query))


def _is_emoji(token: str) -> bool:
    """Short and made only of non-ASCII symbols, so it can never carry markup like ``<b>``."""
    return len(token) <= MAX_EMOJI_LENGTH and all(
        ord(char) > 127 and not char.isalnum() for char in token
    )
