from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock

from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.qr.service import (
    build_full_url,
    generate_qr_png_compact,
    generate_qr_png_full,
    generate_qr_svg_compact,
    generate_qr_svg_full,
    short_code_to_uuid_prefix,
    uuid_to_short_code,
)


def test_uuid_to_short_code():
    item_id = uuid.UUID("12345678-1234-4000-8000-000000000000")
    code = uuid_to_short_code(item_id)
    assert len(code) == 6
    assert code.isprintable()


def test_short_code_roundtrip():
    item_id = uuid.uuid4()
    code = uuid_to_short_code(item_id)
    prefix = short_code_to_uuid_prefix(code)
    assert item_id.hex.startswith(prefix)


def test_short_code_is_url_safe():
    import re
    url_safe_re = re.compile(r"^[0-9A-Za-z_-]+$")
    for _ in range(100):
        code = uuid_to_short_code(uuid.uuid4())
        assert len(code) == 6
        assert url_safe_re.match(code)


def test_build_full_url():
    item_id = uuid.uuid4()
    url = build_full_url(item_id, "http://localhost:8001")
    assert url == f"http://localhost:8001/items/{item_id}"


def test_build_full_url_trailing_slash():
    item_id = uuid.uuid4()
    url = build_full_url(item_id, "http://localhost:8001/")
    assert url == f"http://localhost:8001/items/{item_id}"


def test_generate_qr_png_compact_valid():
    item_id = uuid.uuid4()
    png_bytes = generate_qr_png_compact(item_id)
    assert len(png_bytes) > 0
    img = Image.open(io.BytesIO(png_bytes))
    assert img.format == "PNG"
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_generate_qr_png_full_valid():
    item_id = uuid.uuid4()
    png_bytes = generate_qr_png_full(item_id, "http://localhost:8001")
    assert len(png_bytes) > 0
    img = Image.open(io.BytesIO(png_bytes))
    assert img.format == "PNG"


def test_generate_qr_compact_smaller_than_full():
    item_id = uuid.uuid4()
    compact = generate_qr_png_compact(item_id)
    full = generate_qr_png_full(item_id, "http://localhost:8001")
    assert len(compact) < len(full)


def test_generate_qr_deterministic():
    item_id = uuid.uuid4()
    png1 = generate_qr_png_compact(item_id)
    png2 = generate_qr_png_compact(item_id)
    assert png1 == png2


def test_generate_qr_different_items():
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    png1 = generate_qr_png_compact(id1)
    png2 = generate_qr_png_compact(id2)
    assert png1 != png2


def test_generate_qr_svg_compact_valid():
    item_id = uuid.uuid4()
    svg_bytes = generate_qr_svg_compact(item_id)
    assert len(svg_bytes) > 0
    svg_str = svg_bytes.decode("utf-8")
    assert "<svg" in svg_str


def test_generate_qr_svg_full_valid():
    item_id = uuid.uuid4()
    svg_bytes = generate_qr_svg_full(item_id, "http://localhost:8001")
    assert len(svg_bytes) > 0
    svg_str = svg_bytes.decode("utf-8")
    assert "<svg" in svg_str


async def test_scan_page_requires_auth(client: AsyncClient) -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    from app.main import app

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        response = await client.get("/scan", follow_redirects=False)
        assert response.status_code in (303, 401, 403)
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
