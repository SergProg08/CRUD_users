"""ORM-модель пользователя."""
from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from crud_users.core.database import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Пользователь. Таблица `users`."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # unique=True + index=True -> один UNIQUE INDEX: он и ускоряет поиск по email,
    # и не даёт вставить дубликат (БД выбросит IntegrityError -> наш 409).
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    # Храним только хеш пароля, сам пароль не сохраняется нигде.
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
