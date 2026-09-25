from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.main import app
from app.users.models import User


async def test_admin_index_requires_admin(client: AsyncClient) -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        response = await client.get("/admin", follow_redirects=False)
        assert response.status_code in (303, 401, 403)
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_admin_index_renders(client: AsyncClient) -> None:
    async def override_user():
        return User(
            id=uuid.uuid4(),
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


class _FakeResult:
    def scalar_one_or_none(self):
        return None


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    async def execute(self, *args, **kwargs):
        return _FakeResult()

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


def _override_admin() -> None:
    async def override_user():
        return User(
            id=uuid.uuid4(),
            email="admin@test.com",
            role="admin",
            display_name="Admin",
        )

    app.dependency_overrides[get_current_user] = override_user


async def test_label_settings_requires_admin(client: AsyncClient) -> None:
    response = await client.get("/admin/label-settings", follow_redirects=False)
    assert response.status_code in (303, 401, 403)


async def test_label_settings_page_renders(client: AsyncClient) -> None:
    _override_admin()
    app.dependency_overrides[get_db] = lambda: _FakeSession()
    try:
        response = await client.get("/admin/label-settings")
        assert response.status_code == 200
        assert "Налаштування етикетки" in response.text
        assert 'value="14"' in response.text
        assert 'value="10"' in response.text
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


async def test_label_settings_save_redirects(client: AsyncClient) -> None:
    _override_admin()
    fake = _FakeSession()
    app.dependency_overrides[get_db] = lambda: fake
    try:
        response = await client.post(
            "/admin/label-settings",
            data={
                "label_type": "full",
                "orientation": "vertical",
                "size": "20x50",
                "custom_width": "20",
                "custom_height": "50",
                "name_font_size": "16",
                "code_font_size": "12",
                "max_name_lines": "2",
                "wrap_by_words": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"].endswith("saved=1")
        assert len(fake.added) == 1
        saved = fake.added[0]
        assert saved.max_name_lines == 2
        assert saved.wrap_by_words is True
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


async def test_label_settings_save_rejects_invalid_font(client: AsyncClient) -> None:
    _override_admin()
    fake = _FakeSession()
    app.dependency_overrides[get_db] = lambda: fake
    try:
        response = await client.post(
            "/admin/label-settings",
            data={
                "label_type": "full",
                "orientation": "horizontal",
                "size": "30x15",
                "custom_width": "30",
                "custom_height": "15",
                "name_font_size": "9999",
                "code_font_size": "10",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "error=" in response.headers["location"]
        assert fake.added == []
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


async def test_label_settings_save_unchecked_wrap_by_chars(client: AsyncClient) -> None:
    _override_admin()
    fake = _FakeSession()
    app.dependency_overrides[get_db] = lambda: fake
    try:
        response = await client.post(
            "/admin/label-settings",
            data={
                "label_type": "full",
                "orientation": "horizontal",
                "size": "30x15",
                "custom_width": "30",
                "custom_height": "15",
                "name_font_size": "14",
                "code_font_size": "10",
                "max_name_lines": "4",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert fake.added[0].wrap_by_words is False
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


async def test_label_settings_preview_requires_admin(client: AsyncClient) -> None:
    response = await client.get("/admin/label-settings/preview", follow_redirects=False)
    assert response.status_code in (303, 401, 403)


async def test_label_settings_preview_renders_png(client: AsyncClient) -> None:
    _override_admin()
    try:
        response = await client.get(
            "/admin/label-settings/preview",
            params={
                "label_type": "full",
                "orientation": "vertical",
                "size": "20x50",
                "name_font_size": "18",
                "code_font_size": "12",
                "max_name_lines": "2",
                "wrap_by_words": "0",
                "name": "Тестовий предмет",
                "code": "ZZ99",
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content.startswith(b"\x89PNG")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
