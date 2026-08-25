from __future__ import annotations

from unittest.mock import AsyncMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import AuthService, AuthUser
from app.dependencies import get_db


def test_auth_service_verify_token_invalid() -> None:
    """Test that verify_token returns None for invalid tokens."""
    service = AuthService()
    result = service.verify_token("invalid.token.here")
    assert result is None


def test_auth_user_dataclass() -> None:
    """Test AuthUser dataclass creation."""
    user = AuthUser(supabase_id="abc-123", email="test@example.com")
    assert user.supabase_id == "abc-123"
    assert user.email == "test@example.com"


async def test_login_page_renders(client: AsyncClient) -> None:
    """Test that login page renders."""
    response = await client.get("/auth/login")
    assert response.status_code == 200


async def test_logout_redirects(client: AsyncClient) -> None:
    """Test that logout redirects to login page."""
    response = await client.post("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


async def test_protected_route_without_auth(client: AsyncClient) -> None:
    """Test that admin routes reject unauthenticated requests."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.execute.return_value = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    mock_session.commit = AsyncMock()

    from app.main import app

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        response = await client.get("/admin/users", follow_redirects=False)
        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides.pop(get_db, None)
