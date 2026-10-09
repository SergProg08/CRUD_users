"""Общие фикстуры тестов.

Тесты НЕ трогают PostgreSQL: для каждого теста создаётся своя пустая БД
SQLite в памяти, а `get_session` подменяется через `dependency_overrides`.
"""
from collections.abc import AsyncIterator

import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from crud_users.core.database import Base
from crud_users.core.dependencies import get_session
from crud_users.main import app

# Импорт моделей регистрирует таблицы в Base.metadata (для create_all).
from crud_users.services.users import models as users_models  # noqa: F401


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Чистая БД SQLite в памяти на каждый тест."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        # in-memory БД живёт, пока жива одна connection: используем её для всех сессий
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(engine: AsyncEngine) -> AsyncIterator[httpx.AsyncClient]:
    """HTTP-клиент к приложению, работающий с тестовой БД."""
    session_maker = async_sessionmaker(
        engine, expire_on_commit=False, autoflush=False
    )

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
