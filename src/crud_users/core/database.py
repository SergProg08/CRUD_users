"""
Конфигурация базы данных и базовые модели.

Содержит:
- engine и фабрику сессий (async SQLAlchemy)
- базовый класс `Base` для ORM-моделей с naming conventions
- миксины для полей created_at / updated_at
"""
from datetime import datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql import func

from crud_users.settings import settings

# === NAMING CONVENTIONS ===
# Явные имена индексов и ограничений. Без них БД придумывает имена сама,
# и их сложно ссылаться/менять в миграциях.
NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

# === ENGINE ===
_engine_kwargs: dict = {"echo": settings.DB_ECHO}
if settings.USE_IN_MEMORY_SQLITE:
    # SQLite in-memory живёт, пока жива одна connection. StaticPool заставляет
    # использовать одну и ту же connection во всех сессиях (нужно для тестов).
    _engine_kwargs.update(
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    _engine_kwargs.update(
        pool_pre_ping=True,  # проверять connection перед выдачей из пула
        pool_size=10,        # постоянных соединений в пуле
        max_overflow=20,     # дополнительных при пиковой нагрузке
    )

engine = create_async_engine(settings.database_url, **_engine_kwargs)

# === SESSION FACTORY ===
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # объекты остаются читаемыми после commit
    autoflush=False,         # flush только явно -> более предсказуемо
)


# === BASE MODEL ===
class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""

    metadata = metadata


# === TIMESTAMP MIXINS ===
class CreatedAtMixin:
    """Поле created_at: значение ставит сама БД при INSERT."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UpdatedAtMixin:
    """Поле updated_at: обновляется ORM при каждом UPDATE."""

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )


class TimestampMixin(CreatedAtMixin, UpdatedAtMixin):
    """created_at + updated_at."""
