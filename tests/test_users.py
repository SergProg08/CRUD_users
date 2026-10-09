"""Тесты CRUD-эндпоинтов пользователей."""
import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from crud_users.core.security import verify_password
from crud_users.services.users.models import User

USERS_URL = "/api/v1/users"

USER_DATA = {
    "email": "ann@example.com",
    "full_name": "Ann",
    "password": "secret123",
}


async def create_user(client: httpx.AsyncClient, **overrides) -> dict:
    """Создать пользователя через API и вернуть тело ответа."""
    response = await client.post(USERS_URL, json={**USER_DATA, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def assert_no_secrets(body: dict) -> None:
    """В публичном ответе не должно быть ни пароля, ни его хеша."""
    assert "password" not in body
    assert "password_hash" not in body


async def get_db_user(engine: AsyncEngine, user_id: str) -> User:
    """Прочитать пользователя напрямую из тестовой БД (минуя API)."""
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
        return result.scalar_one()


# --------------------------------------------------------------------------- create


async def test_create_user_returns_public_data(client: httpx.AsyncClient):
    response = await client.post(USERS_URL, json=USER_DATA)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ann@example.com"
    assert body["full_name"] == "Ann"
    assert body["is_active"] is True
    assert body["id"]
    # response_model: в ответе нет ни пароля, ни хеша
    assert_no_secrets(body)


async def test_create_user_normalizes_email_to_lowercase(client: httpx.AsyncClient):
    body = await create_user(client, email="Ann@Example.COM")

    assert body["email"] == "ann@example.com"


async def test_create_user_stores_password_as_hash(
    client: httpx.AsyncClient, engine: AsyncEngine
):
    body = await create_user(client)

    db_user = await get_db_user(engine, body["id"])
    assert db_user.password_hash != "secret123"
    assert verify_password("secret123", db_user.password_hash)


async def test_create_user_with_taken_email_returns_409(client: httpx.AsyncClient):
    await create_user(client)

    # тот же email, но в другом регистре: адрес считается тем же
    response = await client.post(USERS_URL, json={**USER_DATA, "email": "ANN@example.com"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}


@pytest.mark.parametrize(
    "override",
    [
        {"password": "123"},  # короче 8 символов
        {"password": "я" * 40},  # лимит bcrypt в байтах: 80 байт
        {"email": "nope"},
        {"full_name": "   "},
    ],
    ids=["short-password", "password-over-72-bytes", "invalid-email", "blank-name"],
)
async def test_create_user_with_invalid_data_returns_422(
    client: httpx.AsyncClient, override: dict
):
    response = await client.post(USERS_URL, json={**USER_DATA, **override})

    assert response.status_code == 422


async def test_create_user_with_empty_body_returns_422(client: httpx.AsyncClient):
    response = await client.post(USERS_URL, json={})

    assert response.status_code == 422


# ----------------------------------------------------------------------------- read


async def test_get_user_returns_user(client: httpx.AsyncClient):
    created = await create_user(client)

    response = await client.get(f"{USERS_URL}/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["email"] == "ann@example.com"
    assert_no_secrets(body)


async def test_get_missing_user_returns_404(client: httpx.AsyncClient):
    response = await client.get(f"{USERS_URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


async def test_get_user_with_invalid_id_returns_422(client: httpx.AsyncClient):
    response = await client.get(f"{USERS_URL}/not-a-uuid")

    assert response.status_code == 422


async def test_list_users_returns_created(client: httpx.AsyncClient):
    await create_user(client, email="ann@example.com")
    await create_user(client, email="bob@example.com")

    response = await client.get(USERS_URL)

    assert response.status_code == 200
    body = response.json()
    assert {u["email"] for u in body} == {"ann@example.com", "bob@example.com"}
    for user in body:
        assert_no_secrets(user)


async def test_list_users_pagination(client: httpx.AsyncClient):
    for name in ("a", "b", "c"):
        await create_user(client, email=f"{name}@example.com")

    first_page = await client.get(USERS_URL, params={"limit": 2})
    last_page = await client.get(USERS_URL, params={"limit": 2, "offset": 2})

    assert len(first_page.json()) == 2
    assert len(last_page.json()) == 1
    # страницы не пересекаются
    first_ids = {u["id"] for u in first_page.json()}
    assert last_page.json()[0]["id"] not in first_ids


async def test_list_users_with_invalid_limit_returns_422(client: httpx.AsyncClient):
    response = await client.get(USERS_URL, params={"limit": 0})

    assert response.status_code == 422


# --------------------------------------------------------------------------- update


async def test_update_user_changes_only_sent_fields(client: httpx.AsyncClient):
    created = await create_user(client)

    response = await client.patch(f"{USERS_URL}/{created['id']}", json={"full_name": "Ann 2"})

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Ann 2"
    assert body["email"] == "ann@example.com"  # не присылали: не изменился
    assert body["is_active"] is True
    assert body["updated_at"] is not None
    assert_no_secrets(body)


async def test_update_user_can_deactivate(client: httpx.AsyncClient):
    created = await create_user(client)

    response = await client.patch(f"{USERS_URL}/{created['id']}", json={"is_active": False})

    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_update_user_changes_password_hash(
    client: httpx.AsyncClient, engine: AsyncEngine
):
    created = await create_user(client)

    response = await client.patch(f"{USERS_URL}/{created['id']}", json={"password": "newpass123"})

    assert response.status_code == 200
    assert_no_secrets(response.json())
    db_user = await get_db_user(engine, created["id"])
    assert verify_password("newpass123", db_user.password_hash)
    assert not verify_password("secret123", db_user.password_hash)


async def test_update_user_with_same_email_in_other_case_is_ok(client: httpx.AsyncClient):
    created = await create_user(client)

    response = await client.patch(f"{USERS_URL}/{created['id']}", json={"email": "ANN@example.com"})

    assert response.status_code == 200
    assert response.json()["email"] == "ann@example.com"


async def test_update_user_with_taken_email_returns_409(client: httpx.AsyncClient):
    await create_user(client, email="ann@example.com")
    bob = await create_user(client, email="bob@example.com")

    response = await client.patch(f"{USERS_URL}/{bob['id']}", json={"email": "ann@example.com"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}


async def test_update_missing_user_returns_404(client: httpx.AsyncClient):
    response = await client.patch(f"{USERS_URL}/{uuid.uuid4()}", json={"full_name": "Z"})

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


async def test_update_user_with_null_returns_422(client: httpx.AsyncClient):
    created = await create_user(client)

    response = await client.patch(f"{USERS_URL}/{created['id']}", json={"full_name": None})

    assert response.status_code == 422


async def test_update_user_with_empty_body_changes_nothing(client: httpx.AsyncClient):
    created = await create_user(client)

    response = await client.patch(f"{USERS_URL}/{created['id']}", json={})

    assert response.status_code == 200
    assert response.json() == created


# --------------------------------------------------------------------------- delete


async def test_delete_user_returns_204_then_404(client: httpx.AsyncClient):
    created = await create_user(client)

    response = await client.delete(f"{USERS_URL}/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""

    after = await client.get(f"{USERS_URL}/{created['id']}")
    assert after.status_code == 404


async def test_delete_missing_user_returns_404(client: httpx.AsyncClient):
    response = await client.delete(f"{USERS_URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


async def test_deleted_email_can_be_reused(client: httpx.AsyncClient):
    created = await create_user(client)
    await client.delete(f"{USERS_URL}/{created['id']}")

    # после удаления email снова свободен
    await create_user(client)
