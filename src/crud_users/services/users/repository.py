"""Репозиторий пользователей."""
from crud_users.common.repository import SQLAlchemyRepository
from crud_users.services.users.models import User


class UserRepository(SQLAlchemyRepository[User]):
    """Доступ к таблице `users`."""

    model = User

    async def find_by_email(self, email: str) -> User | None:
        """Найти пользователя по email."""
        return await self.find_one(email=email)

    async def list_users(self, *, limit: int = 100, offset: int = 0) -> list[User]:
        """Список пользователей: сначала старые, при равенстве - по id."""
        return await self.find_all(
            limit=limit,
            offset=offset,
            order_by=(User.created_at, User.id),
        )
