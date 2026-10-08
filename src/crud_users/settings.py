"""Настройки приложения."""
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Глобальные настройки приложения.

    Значения читаются из переменных окружения и файла `.env`.
    Имена полей регистронезависимы: `DB_HOST` в `.env` -> `settings.DB_HOST`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === APPLICATION ===
    ENVIRONMENT: Literal["DEV", "PROD"] = "DEV"

    #: in-memory SQLite (для pytest без PostgreSQL)
    USE_IN_MEMORY_SQLITE: bool = False

    # === DATABASE ===
    # Значения по умолчанию совпадают с docker-compose.yaml
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "crud_users"
    DB_USER: str = "crud_user"
    DB_PASS: str = "crud_password"
    DB_ECHO: bool = False

    @property
    def database_url(self) -> str:
        """URL подключения к БД для SQLAlchemy (async-драйвер)."""
        if self.USE_IN_MEMORY_SQLITE:
            return "sqlite+aiosqlite://"
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
