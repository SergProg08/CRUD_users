"""Unit-тесты схем и мелких функций сервиса: без БД, без HTTP."""
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from crud_users.services.users.models import User
from crud_users.services.users.schemas import UserCreate, UserPublic, UserUpdate
from crud_users.services.users.service import normalize_email

VALID = {"email": "ann@example.com", "full_name": "Ann", "password": "secret123"}


# ------------------------------------------------------------------------ UserCreate


def test_user_create_accepts_valid_data():
    user = UserCreate(**VALID)

    assert user.email == "ann@example.com"
    assert user.full_name == "Ann"


@pytest.mark.parametrize(
    "override",
    [
        {"email": "nope"},
        {"full_name": ""},
        {"full_name": "   "},  # пробелы обрезаются -> пустая строка
        {"full_name": "x" * 256},
        {"password": "1234567"},  # 7 символов
        {"password": "a" * 73},  # больше лимита bcrypt
        {"password": "я" * 40},  # 80 байт
    ],
    ids=[
        "bad-email",
        "empty-name",
        "blank-name",
        "name-too-long",
        "password-too-short",
        "password-73-bytes",
        "password-cyrillic-80-bytes",
    ],
)
def test_user_create_rejects_invalid_data(override: dict):
    with pytest.raises(ValidationError):
        UserCreate(**{**VALID, **override})


@pytest.mark.parametrize("missing", ["email", "full_name", "password"])
def test_user_create_requires_all_fields(missing: str):
    data = {k: v for k, v in VALID.items() if k != missing}

    with pytest.raises(ValidationError):
        UserCreate(**data)


# ------------------------------------------------------------------------ UserUpdate


def test_user_update_without_fields_is_empty():
    assert UserUpdate().model_dump(exclude_unset=True) == {}


def test_user_update_keeps_only_sent_fields():
    update = UserUpdate(full_name="Bob", is_active=False)

    assert update.model_dump(exclude_unset=True) == {"full_name": "Bob", "is_active": False}


@pytest.mark.parametrize("field", ["email", "full_name", "password", "is_active"])
def test_user_update_rejects_explicit_null(field: str):
    with pytest.raises(ValidationError):
        UserUpdate(**{field: None})


@pytest.mark.parametrize(
    "override",
    [{"password": "short"}, {"password": "a" * 73}, {"email": "nope"}, {"full_name": ""}],
    ids=["password-too-short", "password-73-bytes", "bad-email", "empty-name"],
)
def test_user_update_rejects_invalid_data(override: dict):
    with pytest.raises(ValidationError):
        UserUpdate(**override)


# ------------------------------------------------------------------------ UserPublic


def test_user_public_has_no_secret_fields():
    assert "password" not in UserPublic.model_fields
    assert "password_hash" not in UserPublic.model_fields


def test_user_public_is_built_from_orm_object_without_hash():
    orm_user = User(
        id=uuid.uuid4(),
        email="ann@example.com",
        full_name="Ann",
        password_hash="$2b$12$secret-hash",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )

    public = UserPublic.model_validate(orm_user)

    assert public.id == orm_user.id
    assert "secret-hash" not in public.model_dump_json()


# --------------------------------------------------------------------- normalize_email


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Ann@Example.com", "ann@example.com"),
        ("  ann@example.com  ", "ann@example.com"),
        ("ANN@EXAMPLE.COM", "ann@example.com"),
        ("ann@example.com", "ann@example.com"),
    ],
)
def test_normalize_email(raw: str, expected: str):
    assert normalize_email(raw) == expected
