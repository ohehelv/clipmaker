"""SQLAlchemy 2.0 async engine + session."""

from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings


_engine = create_async_engine(settings.database_url, echo=False, future=True)
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


def get_engine():
    return _engine


def get_sessionmaker():
    return _SessionLocal


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _SessionLocal() as s:
        yield s


async def init_db() -> None:
    """Создать таблицы (без Alembic, для простоты)."""
    from . import models  # noqa: F401 — регистрация моделей в Base.metadata
    from .models import Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
