"""Unit-тесты хеширования паролей: без БД, без HTTP."""
import pytest

from crud_users.core.security import (
    ahash_password,
    averify_password,
    hash_password,
    password_fits_bcrypt,
    verify_password,
)


def test_hash_password_is_not_plaintext():
    hashed = hash_password("secret123")

    assert hashed != "secret123"
    assert hashed.startswith("$2b$")  # формат bcrypt
    assert len(hashed) == 60


def test_hash_password_uses_random_salt():
    # один пароль -> разные хеши, но оба проходят проверку
    first, second = hash_password("secret123"), hash_password("secret123")

    assert first != second
    assert verify_password("secret123", first)
    assert verify_password("secret123", second)


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("secret123")

    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong-password", hashed) is False


@pytest.mark.parametrize(
    ("password", "expected"),
    [
        ("", True),
        ("a" * 72, True),  # ровно по лимиту
        ("a" * 73, False),
        ("я" * 36, True),  # 36 символов * 2 байта = 72 байта
        ("я" * 36 + "a", False),  # 73 байта: считаем байты, а не символы
    ],
    ids=["empty", "72-bytes", "73-bytes", "cyrillic-72-bytes", "cyrillic-73-bytes"],
)
def test_password_fits_bcrypt_counts_bytes(password: str, expected: bool):
    assert password_fits_bcrypt(password) is expected


def test_hash_password_too_long_raises():
    with pytest.raises(ValueError):
        hash_password("a" * 73)


def test_verify_password_too_long_returns_false():
    # такой пароль мы не смогли бы сохранить, значит, он заведомо неверный
    hashed = hash_password("secret123")

    assert verify_password("a" * 73, hashed) is False


async def test_async_wrappers_work():
    hashed = await ahash_password("secret123")

    assert await averify_password("secret123", hashed) is True
    assert await averify_password("wrong-password", hashed) is False
