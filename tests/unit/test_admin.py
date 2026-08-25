from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.main import app
from app.users.models import User


async def test_admin_index_requires_admin(client: AsyncClient) -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        response = await client.get("/admin", follow_redirects=False)
        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_admin_index_renders(client: AsyncClient) -> None:
    from app.dependencies import get_current_user

    async def override_user():
        return User(
            id=uuid.uuid4(),
            supabase_id="test-sb-id",
            email="admin@test.com",
            role="admin",
            display_name="Admin",
        )

    app.dependency_overrides[get_current_user] = override_user
    try:
        response = await client.get("/admin")
        assert response.status_code == 200
        assert "Адміністрування" in response.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)
