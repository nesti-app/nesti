from __future__ import annotations

import io
import uuid

from PIL import Image

from app.qr.service import build_qr_url, generate_qr_png, generate_qr_svg


def test_build_qr_url():
    item_id = uuid.uuid4()
    url = build_qr_url(item_id)
    assert str(item_id) in url
    assert url.endswith(f"/items/{item_id}")


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
