"""
Точка входа FastAPI.

Запуск (из корня проекта):
    uv run uvicorn crud_users.main:app --reload

Схему БД создаёт Alembic, перед первым запуском: `uv run alembic upgrade head`.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from loguru import logger

from crud_users.core.database import engine
from crud_users.services.users.router import router as users_router
from crud_users.settings import settings

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Старт и корректное завершение приложения."""
    logger.info(
        f"Запуск: {settings.ENVIRONMENT} "
        f"({settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME})"
    )
    yield
    # Закрываем пул соединений с БД
    await engine.dispose()
    logger.info("Остановка приложения")


app = FastAPI(
    title="CRUD Users API",
    description="CRUD операции над пользователями.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(users_router, prefix=API_V1_PREFIX)


@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    """Проверка, что приложение запущено."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}
