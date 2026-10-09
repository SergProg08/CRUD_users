"""
Хеширование и проверка паролей (bcrypt).

bcrypt намеренно медленный (~0.2 с на хеш) - так перебор паролей становится
дорогим. Но это CPU-bound операция: в async-коде её нельзя вызывать напрямую,
иначе event loop заблокируется и все остальные запросы будут ждать.
Поэтому для async-кода есть обёртки `ahash_password` / `averify_password`,
которые выносят работу в отдельный поток.
"""
import asyncio

import bcrypt

#: Ограничение алгоритма bcrypt: учитываются только первые 72 БАЙТА пароля.
BCRYPT_MAX_PASSWORD_BYTES = 72


def password_fits_bcrypt(password: str) -> bool:
    """Помещается ли пароль в лимит bcrypt (считаем байты UTF-8, а не символы)."""
    return len(password.encode("utf-8")) <= BCRYPT_MAX_PASSWORD_BYTES


def hash_password(password: str) -> str:
    """Захешировать пароль. Соль генерируется автоматически и входит в результат."""
    if not password_fits_bcrypt(password):
        raise ValueError(f"Пароль длиннее {BCRYPT_MAX_PASSWORD_BYTES} байт")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Проверить пароль по сохранённому хешу."""
    if not password_fits_bcrypt(password):
        # Такой пароль мы никогда не могли сохранить, значит, он неверный.
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


async def ahash_password(password: str) -> str:
    """`hash_password` без блокировки event loop."""
    return await asyncio.to_thread(hash_password, password)


async def averify_password(password: str, password_hash: str) -> bool:
    """`verify_password` без блокировки event loop."""
    return await asyncio.to_thread(verify_password, password, password_hash)
