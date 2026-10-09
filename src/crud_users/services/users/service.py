"""Бизнес-логика пользователей."""
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from crud_users.core.security import ahash_password
from crud_users.services.users.models import User
from crud_users.services.users.repository import UserRepository
from crud_users.services.users.schemas import UserCreate, UserUpdate


# Доменные исключения. Сервис ничего не знает про HTTP: роутер превращает
# их в статусы 404 / 409.
class UserNotFoundError(Exception):
    """Пользователь с таким id не найден."""


class EmailAlreadyExistsError(Exception):
    """Пользователь с таким email уже существует."""


def normalize_email(email: str) -> str:
    """Email без учёта регистра: A@b.co и a@b.co - один и тот же адрес."""
    return email.strip().lower()


class UserService:
    """CRUD пользователей. Сервис управляет транзакцией (commit/rollback)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def create(self, data: UserCreate) -> User:
        email = normalize_email(data.email)
        await self._ensure_email_free(email)

        user_data = {
            "email": email,
            "full_name": data.full_name,
            "password_hash": await ahash_password(data.password),
        }
        try:
            user = await self.users.add(user_data)
            await self.session.commit()
        except IntegrityError:
            # Гонка: другой запрос успел занять email между проверкой и INSERT.
            await self.session.rollback()
            raise EmailAlreadyExistsError(email) from None
        return user

    async def get(self, user_id: uuid.UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    async def list_users(self, *, limit: int = 100, offset: int = 0) -> list[User]:
        return await self.users.list_users(limit=limit, offset=offset)

    async def update(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = await self.get(user_id)

        # Только присланные поля. null уже отсечён схемой (422).
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return user

        if "email" in changes:
            changes["email"] = normalize_email(changes["email"])
            if changes["email"] != user.email:
                await self._ensure_email_free(changes["email"])
        if "password" in changes:
            # В БД хранится только хеш, поле password в модели не существует.
            changes["password_hash"] = await ahash_password(changes.pop("password"))

        try:
            user = await self.users.update(user, changes)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise EmailAlreadyExistsError(changes.get("email")) from None
        return user

    async def delete(self, user_id: uuid.UUID) -> None:
        user = await self.get(user_id)
        await self.users.delete(user)
        await self.session.commit()

    async def _ensure_email_free(self, email: str) -> None:
        """Быстрая проверка до INSERT/UPDATE. Окончательно защищает уникальный индекс."""
        if await self.users.find_by_email(email) is not None:
            raise EmailAlreadyExistsError(email)
