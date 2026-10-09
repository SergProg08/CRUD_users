"""
Базовый репозиторий (паттерн Repository).

Репозиторий - единственное место, где пишутся запросы к БД. Сервисы вызывают
его методы и ничего не знают про SQL. Репозиторий НЕ делает commit: транзакцией
управляет сервис, чтобы несколько операций можно было выполнить атомарно.
"""
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud_users.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class SQLAlchemyRepository(Generic[ModelType]):
    """Базовые операции над одной ORM-моделью.

    Использование:
        class UserRepository(SQLAlchemyRepository[User]):
            model = User
    """

    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, data: dict[str, Any]) -> ModelType:
        """Создать запись. flush отправляет INSERT в БД (без commit)."""
        obj = self.model(**data)
        self.session.add(obj)
        # flush: INSERT выполняется сейчас, поэтому уникальные ограничения
        # проверяются здесь (IntegrityError), а id и created_at уже заполнены.
        await self.session.flush()
        return obj

    async def get(self, id_: Any) -> ModelType | None:
        """Найти запись по первичному ключу."""
        return await self.session.get(self.model, id_)

    async def find_one(self, **filters: Any) -> ModelType | None:
        """Найти одну запись по равенству полей: find_one(email="a@b.co")."""
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: Sequence[Any] = (),
    ) -> list[ModelType]:
        """Список записей с пагинацией. Без order_by порядок не гарантирован."""
        stmt = select(self.model).order_by(*order_by).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, obj: ModelType, data: dict[str, Any]) -> ModelType:
        """Обновить поля уже загруженного объекта."""
        for field, value in data.items():
            setattr(obj, field, value)
        await self.session.flush()
        # updated_at ставит БД (onupdate=func.now()): после UPDATE значение
        # "просрочено", а в async его нельзя дочитать неявно, поэтому refresh.
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        """Удалить загруженный объект."""
        await self.session.delete(obj)
        await self.session.flush()
