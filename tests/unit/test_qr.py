from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock

from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.qr.service import build_qr_url, generate_qr_png, generate_qr_svg


def test_build_qr_url():
    item_id = uuid.uuid4()
    url = build_qr_url(item_id)
    assert str(item_id) in url
    assert url.endswith(f"/items/{item_id}")


def test_build_qr_url_uses_app_url():
    item_id = uuid.uuid4()
    url = build_qr_url(item_id)
    assert url.startswith("http://localhost:8000/items/")


def test_generate_qr_png_valid():
    item_id = uuid.uuid4()
    png_bytes = generate_qr_png(item_id)
    assert len(png_bytes) > 0
    img = Image.open(io.BytesIO(png_bytes))
    assert img.format == "PNG"
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_generate_qr_deterministic():
    item_id = uuid.uuid4()
    png1 = generate_qr_png(item_id)
    png2 = generate_qr_png(item_id)
    assert png1 == png2


def test_generate_qr_different_items():
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    png1 = generate_qr_png(id1)
    png2 = generate_qr_png(id2)
    assert png1 != png2


def test_generate_qr_svg_valid():
    item_id = uuid.uuid4()
    svg_bytes = generate_qr_svg(item_id)
    assert len(svg_bytes) > 0
    svg_str = svg_bytes.decode("utf-8")
    assert "<svg" in svg_str
    assert "qr-path" in svg_str


async def test_scan_page_requires_auth(client: AsyncClient) -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    from app.main import app

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        response = await client.get("/scan", follow_redirects=False)
        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_scan_page_renders(client: AsyncClient) -> None:
    from app.dependencies import get_current_user
    from app.main import app
    from app.users.models import User

    async def override_user():
        return User(
            id=uuid.uuid4(),
            supabase_id="test-sb-id",
            email="test@example.com",
            role="editor",
            display_name="Test",
        )

    app.dependency_overrides[get_current_user] = override_user
    try:
        response = await client.get("/scan")
        assert response.status_code == 200
        body = response.text
        assert "Сканувати QR-код" in body
        assert "manual-form" in body
        assert "jsQR" in body
    finally:
        app.dependency_overrides.pop(get_current_user, None)
