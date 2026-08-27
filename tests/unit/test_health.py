from __future__ import annotations

from httpx import AsyncClient

from app.db.engine import _async_database_url


def test_async_database_url_normalizes_driver() -> None:
    """Plain postgres URLs are rewritten to use the asyncpg driver."""
    assert _async_database_url("postgres://u:p@h/db") == "postgresql+asyncpg://u:p@h/db"
    assert (
        _async_database_url("postgresql://u:p@h/db")
        == "postgresql+asyncpg://u:p@h/db"
    )
    assert (
        _async_database_url("postgresql+psycopg2://u:p@h/db")
        == "postgresql+asyncpg://u:p@h/db"
    )
    assert (
        _async_database_url("postgresql+asyncpg://u:p@h/db")
        == "postgresql+asyncpg://u:p@h/db"
    )


def test_async_database_url_adds_ssl_for_supabase() -> None:
    """Supabase Cloud URLs get ssl=require added for TLS."""
    result = _async_database_url(
        "postgresql://postgres.abc:pw@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true"
    )
    assert result.startswith("postgresql+asyncpg://")
    assert "ssl=require" in result
    assert "pgbouncer=true" in result

    # Existing ssl should not be duplicated
    result2 = _async_database_url(
        "postgresql+asyncpg://u:p@db.x.supabase.co:5432/postgres?ssl=require"
    )
    assert result2.count("ssl") == 1


def test_async_database_url_keeps_local_url_unchanged() -> None:
    """Local/non-Supabase URLs only get the driver normalized, no SSL forced."""
    assert _async_database_url(
        "postgresql://postgres:postgres@localhost:5432/db"
    ) == "postgresql+asyncpg://postgres:postgres@localhost:5432/db"


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_index_redirects_to_dashboard(client: AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert "/dashboard" in response.headers["location"]


async def test_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get("/nonexistent")
    assert response.status_code == 404
