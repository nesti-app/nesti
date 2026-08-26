from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime

import pytest
from PIL import Image

from app.common.exceptions import ConflictError
from app.media.schemas import ImageReorderItem, ImageUploadResponse
from app.media.service import (
    _resize_within,
    _to_webp,
    generate_storage_paths,
    process_image,
    validate_upload,
)


def _make_test_image(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_validate_upload_ok():
    data = _make_test_image()
    validate_upload("photo.jpg", "image/jpeg", len(data))


def test_validate_upload_too_large():
    with pytest.raises(ConflictError, match="File too large"):
        validate_upload("big.jpg", "image/jpeg", 100_000_000)


def test_validate_upload_bad_type():
    with pytest.raises(ConflictError, match="Unsupported"):
        validate_upload("file.exe", "application/octet-stream", 100)


def test_validate_upload_blocked_ext():
    with pytest.raises(ConflictError, match="Blocked"):
        validate_upload("virus.exe", "image/jpeg", 100)


def test_process_image_creates_webp():
    data = _make_test_image(200, 150)
    result = process_image(data, "image/jpeg")
    assert result["mime_type"] == "image/webp"
    assert result["optimized"] is not None
    assert result["thumbnail"] is not None
    assert result["optimized_width"] <= 2400
    assert result["thumbnail_width"] <= 256


def test_process_image_small():
    data = _make_test_image(50, 50)
    result = process_image(data, "image/jpeg")
    assert result["optimized_width"] == 50
    assert result["optimized_height"] == 50


def test_resize_within_no_change():
    img = Image.new("RGB", (100, 100))
    resized = _resize_within(img, 200)
    assert resized.size == (100, 100)


def test_resize_within_downscale():
    img = Image.new("RGB", (1000, 500))
    resized = _resize_within(img, 256)
    assert resized.size[0] <= 256
    assert resized.size[1] <= 256


def test_to_webp():
    img = Image.new("RGB", (100, 100), "blue")
    data, w, h = _to_webp(img)
    assert len(data) > 0
    assert w == 100
    assert h == 100


def test_generate_storage_paths():
    item_id = uuid.uuid4()
    image_id = uuid.uuid4()
    opt, thumb = generate_storage_paths(item_id, image_id)
    assert opt == f"{item_id}/{image_id}-optimized.webp"
    assert thumb == f"{item_id}/{image_id}-thumbnail.webp"


def test_generate_storage_paths_no_image_id():
    item_id = uuid.uuid4()
    opt, thumb = generate_storage_paths(item_id)
    assert opt.startswith(f"{item_id}/")
    assert opt.endswith("-optimized.webp")
    assert thumb.endswith("-thumbnail.webp")


def test_upload_response_schema():
    resp = ImageUploadResponse(
        id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        storage_path="test/optimized.webp",
        mime_type="image/webp",
        width=800,
        height=600,
        size_bytes=50000,
        sort_order=0,
        is_primary=True,
        created_at=datetime.now(UTC),
    )
    assert resp.is_primary is True


def test_reorder_item_schema():
    item = ImageReorderItem(id=uuid.uuid4(), sort_order=2)
    assert item.sort_order == 2
