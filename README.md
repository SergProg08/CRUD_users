# CRUD Users

REST API для управления пользователями: FastAPI, async SQLAlchemy 2.0, PostgreSQL, Alembic.

## Возможности

- CRUD над пользователями: создание, чтение (один и список), частичное обновление, удаление.
- Отдельные схемы: `UserCreate` (вход при создании), `UserUpdate` (частичное обновление), `UserPublic` (ответ).
- В ответах никогда нет пароля и его хеша (`response_model=UserPublic`).
- Пароли хранятся только в виде хеша bcrypt.
- Email уникален без учёта регистра: `409 Conflict` при конфликте, `404 Not Found`, если пользователя нет.
- Сессия БД выдаётся через зависимость FastAPI (`Depends(get_session)`), по одной на запрос.

## Стек

Python 3.12, FastAPI, SQLAlchemy 2.0 (asyncio) + asyncpg, PostgreSQL 16, Alembic, Pydantic v2,
bcrypt, loguru, pytest. Менеджер зависимостей: [uv](https://docs.astral.sh/uv/).

## Быстрый старт

```bash
# 1. Зависимости
uv sync

# 2. Настройки (значения по умолчанию подходят для docker-compose)
cp .env.example .env

# 3. PostgreSQL
docker compose up -d

# 4. Схема БД
uv run alembic upgrade head

# 5. Запуск
uv run uvicorn crud_users.main:app --reload
```

После запуска:

- Swagger UI: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

## Настройки

Читаются из переменных окружения и файла `.env` (см. `.env.example`).

| Переменная | По умолчанию | Описание |
|---|---|---|
| `ENVIRONMENT` | `DEV` | `DEV` или `PROD` |
| `DB_HOST` | `localhost` | хост PostgreSQL |
| `DB_PORT` | `5432` | порт |
| `DB_NAME` | `crud_users` | имя базы |
| `DB_USER` | `crud_user` | пользователь |
| `DB_PASS` | `crud_password` | пароль (в `PROD` обязательно переопределить) |
| `DB_ECHO` | `false` | логировать SQL |

## API

Префикс: `/api/v1`.

| Метод и путь | Успех | Ошибки | Описание |
|---|---|---|---|
| `POST /users` | `201` | `409` email занят, `422` | создать пользователя |
| `GET /users?limit=10&offset=0` | `200` | `422` | список (`limit` 1-100) |
| `GET /users/{user_id}` | `200` | `404`, `422` | получить по id |
| `PATCH /users/{user_id}` | `200` | `404`, `409`, `422` | обновить присланные поля |
| `DELETE /users/{user_id}` | `204` | `404` | удалить |

Пример:

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{"email": "ann@example.com", "full_name": "Ann", "password": "secret123"}'
```

```json
{
  "id": "6abb6021-9538-4353-868f-cc717ab36494",
  "email": "ann@example.com",
  "full_name": "Ann",
  "is_active": true,
  "created_at": "2026-10-09T09:28:56.262363Z",
  "updated_at": null
}
```

Правила валидации:

- `password`: от 8 символов и не более 72 **байт** (ограничение bcrypt; кириллица занимает 2 байта на символ).
- `full_name`: от 1 до 255 символов, пробелы по краям обрезаются.
- `PATCH`: поля можно не присылать, но нельзя присылать со значением `null` (ответ `422`).
- `email` приводится к нижнему регистру.

## Структура проекта

```
src/crud_users/
  main.py                  # приложение FastAPI, lifespan, /health
  settings.py              # настройки (pydantic-settings)
  core/
    database.py            # engine, фабрика сессий, Base, TimestampMixin
    dependencies.py        # get_session и SessionDep
    schemas.py             # BaseSchema, TimestampSchema
    security.py            # хеширование паролей (bcrypt)
  common/
    repository.py          # базовый SQLAlchemyRepository
  services/users/
    models.py              # ORM-модель User
    schemas.py             # UserCreate, UserUpdate, UserPublic
    repository.py          # запросы к БД
    service.py             # бизнес-логика, транзакции, доменные исключения
    router.py              # HTTP-эндпоинты
migrations/                # Alembic
tests/                     # pytest
```

Слои: `router` -> `service` -> `repository` -> БД.

- **router** знает про HTTP: переводит доменные исключения в `404` и `409`.
- **service** содержит бизнес-логику и управляет транзакцией (`commit` / `rollback`).
- **repository** содержит только запросы к БД и не делает `commit`.

## Миграции

```bash
uv run alembic revision --autogenerate -m "описание"   # создать миграцию по изменениям моделей
uv run alembic upgrade head                            # применить все
uv run alembic downgrade -1                            # откатить последнюю
uv run alembic current                                 # текущая ревизия
uv run alembic check                                   # есть ли расхождения моделей и БД
```

Новые модели нужно импортировать в `migrations/env.py`, иначе autogenerate их не увидит.

## Тесты

```bash
uv run pytest -v
```

Тесты не используют PostgreSQL: для каждого теста создаётся пустая SQLite в памяти, а `get_session`
подменяется через `app.dependency_overrides`.

- `tests/test_security.py`, `tests/test_schemas.py`: unit-тесты (хеширование, схемы, нормализация email).
- `tests/test_users.py`: API-тесты всех эндпоинтов, включая `404`, `409`, `422` и отсутствие хеша в ответах.

## Полезные команды

```bash
docker compose up -d        # запустить PostgreSQL
docker compose down         # остановить (данные сохраняются)
docker compose down -v      # остановить и удалить данные
```
