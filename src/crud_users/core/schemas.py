"""Общие Pydantic-схемы."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Базовая схема для всех Pydantic-моделей проекта.

    - from_attributes: схему можно создать из ORM-объекта
      (`UserPublic.model_validate(user)`), а не только из dict.
    - str_strip_whitespace: пробелы по краям строк обрезаются автоматически.
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Схема с временными метками для ответов API."""

    created_at: datetime
    updated_at: datetime | None = None
