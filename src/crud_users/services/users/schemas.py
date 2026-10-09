"""Pydantic-схемы пользователя: вход (Create/Update) и выход (Public)."""
import uuid

from pydantic import EmailStr, Field, field_validator, model_validator

from crud_users.core.schemas import BaseSchema, TimestampSchema
from crud_users.core.security import BCRYPT_MAX_PASSWORD_BYTES, password_fits_bcrypt

PASSWORD_TOO_LONG_MESSAGE = f"Пароль не должен превышать {BCRYPT_MAX_PASSWORD_BYTES} байта"


def _check_password_length(value: str | None) -> str | None:
    """Общая проверка пароля. `None` пропускаем: поле необязательное (PATCH)."""
    if value is not None and not password_fits_bcrypt(value):
        raise ValueError(PASSWORD_TOO_LONG_MESSAGE)
    return value


class UserCreate(BaseSchema):
    """Тело запроса на создание пользователя. Все поля обязательны."""

    email: EmailStr = Field(description="Email пользователя")
    full_name: str = Field(
        min_length=1, max_length=255, description="Полное имя пользователя"
    )
    password: str = Field(min_length=8, description="Пароль (хранится только хеш)")

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _check_password_length(value)


class UserUpdate(BaseSchema):
    """Тело запроса на частичное обновление. Все поля необязательны.

    `None` по умолчанию означает «поле не прислали»; сервис берёт только
    присланные поля через `model_dump(exclude_unset=True)`.
    """

    email: EmailStr | None = Field(None, description="Email пользователя")
    full_name: str | None = Field(
        None, min_length=1, max_length=255, description="Полное имя пользователя"
    )
    password: str | None = Field(
        None, min_length=8, description="Новый пароль (хранится только хеш)"
    )
    is_active: bool | None = Field(None, description="Активен ли пользователь")

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        return _check_password_length(value)

    @model_validator(mode="after")
    def forbid_explicit_null(self) -> "UserUpdate":
        """Поле можно не присылать, но нельзя присылать со значением null:
        все эти колонки в БД NOT NULL."""
        nulls = sorted(f for f in self.model_fields_set if getattr(self, f) is None)
        if nulls:
            raise ValueError(f"Поля не могут быть null: {', '.join(nulls)}")
        return self


class UserPublic(TimestampSchema):
    """Ответ API. Намеренно без `password` и `password_hash`."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
