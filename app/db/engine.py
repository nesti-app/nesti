from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _async_database_url(get_settings().database_url),
            echo=get_settings().is_development,
            pool_pre_ping=True,
        )
    return _engine


def _async_database_url(database_url: str) -> str:
    """Normalize a PostgreSQL URL for the asyncpg driver.

    - Rewrites plain `postgres://` / `postgresql://` (which SQLAlchemy maps to
      the sync psycopg2 driver) to `postgresql+asyncpg://`.
    - Ensures `ssl=require` is present for Supabase Cloud hosts, which require
      TLS (asyncpg does not enable SSL by default).
    """
    if database_url.startswith("postgresql+psycopg2://"):
        database_url = database_url.replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://", 1
        )
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql+asyncpg://", 1
        )

    if "supabase.co" in database_url and "ssl=" not in database_url:
        if "?" in database_url:
            database_url += "&ssl=require"
        else:
            database_url += "?ssl=require"

    return database_url


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
