"""HTTP-эндпоинты пользователей."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from crud_users.core.dependencies import SessionDep
from crud_users.services.users.schemas import UserCreate, UserPublic, UserUpdate
from crud_users.services.users.service import (
    EmailAlreadyExistsError,
    UserNotFoundError,
    UserService,
)


def get_user_service(session: SessionDep) -> UserService:
    """Собрать сервис поверх сессии текущего запроса."""
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]

router = APIRouter(prefix="/users", tags=["Users"])

# Тексты ошибок в одном месте: роутер превращает доменные исключения в HTTP.
USER_NOT_FOUND = "User not found"
EMAIL_TAKEN = "Email already registered"


@router.post(
    "",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Создать пользователя",
    responses={status.HTTP_409_CONFLICT: {"description": EMAIL_TAKEN}},
)
async def create_user(data: UserCreate, service: UserServiceDep):
    try:
        return await service.create(data)
    except EmailAlreadyExistsError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN) from None


@router.get(
    "",
    response_model=list[UserPublic],
    summary="Список пользователей",
)
async def list_users(
    service: UserServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await service.list_users(limit=limit, offset=offset)


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Получить пользователя по id",
    responses={status.HTTP_404_NOT_FOUND: {"description": USER_NOT_FOUND}},
)
async def get_user(user_id: uuid.UUID, service: UserServiceDep):
    try:
        return await service.get(user_id)
    except UserNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND) from None


@router.patch(
    "/{user_id}",
    response_model=UserPublic,
    summary="Частично обновить пользователя",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": USER_NOT_FOUND},
        status.HTTP_409_CONFLICT: {"description": EMAIL_TAKEN},
    },
)
async def update_user(user_id: uuid.UUID, data: UserUpdate, service: UserServiceDep):
    try:
        return await service.update(user_id, data)
    except UserNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND) from None
    except EmailAlreadyExistsError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN) from None


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя",
    responses={status.HTTP_404_NOT_FOUND: {"description": USER_NOT_FOUND}},
)
async def delete_user(user_id: uuid.UUID, service: UserServiceDep) -> None:
    try:
        await service.delete(user_id)
    except UserNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND) from None
