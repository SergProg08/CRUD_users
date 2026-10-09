"""
Зависимости (dependencies) FastAPI.

`get_session` выдаёт сессию БД на время одного HTTP-запроса и гарантированно
закрывает её после. Хранить сессию глобально нельзя: она не потокобезопасна и
не рассчитана на одновременное использование из разных запросов.
"""
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from crud_users.core.database import async_session_maker


async def get_session() -> AsyncIterator[AsyncSession]:
    """Открыть сессию на запрос; закрыть её после обработки.

    Всё, что до `yield`, выполняется перед обработчиком, а после `yield` -
    когда запрос обработан (в том числе при исключении).

    Если транзакция не была зафиксирована (`commit`), при закрытии сессии
    все её изменения откатываются. Фиксирует транзакцию сервис.
    """
    async with async_session_maker() as session:
        yield session


#: Короткая аннотация для обработчиков и зависимостей:
#:     async def handler(session: SessionDep): ...
SessionDep = Annotated[AsyncSession, Depends(get_session)]
