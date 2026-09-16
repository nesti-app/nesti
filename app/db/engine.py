from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy import event, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _is_sqlite(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def _async_database_url(database_url: str) -> str:
    """Normalize a plain database URL for the appropriate async driver.

    PostgreSQL:  postgresql:// / postgresql+psycopg2:// → postgresql+asyncpg://
    SQLite:      sqlite:// → sqlite+aiosqlite://
    """
    if database_url.startswith("sqlite://"):
        return database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://", 1
        )
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return database_url


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = _async_database_url(get_settings().database_url)
        is_sqlite = _is_sqlite(url)

        if is_sqlite:
            db_path = str(make_url(url).database)
            if db_path and db_path != ":memory:":
                os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
            _engine = create_async_engine(
                url,
                echo=get_settings().is_development,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
            )

            @event.listens_for(_engine.sync_engine, "connect")
            def _set_sqlite_pragma(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
                dbapi_conn.execute("PRAGMA foreign_keys = ON")
        else:
            _engine = create_async_engine(
                url,
                echo=get_settings().is_development,
                pool_pre_ping=True,
            )
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession]:
    session_factory = _get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
