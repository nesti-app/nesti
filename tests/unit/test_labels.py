from __future__ import annotations

import uuid

from app.labels.schemas import LABEL_PRESETS, LabelRequest, LabelSize
from app.labels.service import generate_label_compact, generate_label_full, mm_to_px
from app.qr.service import uuid_to_short_code


def test_mm_to_px():
    assert mm_to_px(25, 203) == 199
    assert mm_to_px(25.4, 203) == 203
    assert mm_to_px(1, 203) == 7


def test_label_size_presets():
    assert "12x30" in LABEL_PRESETS
    assert "15x30" in LABEL_PRESETS
    assert "15x40" in LABEL_PRESETS
    assert "20x30" in LABEL_PRESETS
    assert "20x50" in LABEL_PRESETS
    assert len(LABEL_PRESETS) == 10


def test_label_request_preset():
    req = LabelRequest(size=LabelSize.MEDIUM_15x30)
    w, h = req.get_dimensions_mm()
    assert w == 15
    assert h == 30


def test_label_request_custom():
    req = LabelRequest(size=LabelSize.CUSTOM, custom_width_mm=25, custom_height_mm=60)
    w, h = req.get_dimensions_mm()
    assert w == 25
    assert h == 60


def test_label_request_custom_defaults():
    req = LabelRequest(size=LabelSize.CUSTOM)
    w, h = req.get_dimensions_mm()
    assert w == 20
    assert h == 50


def test_generate_label_compact_vertical():
    item_id = uuid.uuid4()
    code = uuid_to_short_code(item_id)
    png = generate_label_compact(item_id, "Test Item", code, 15, 30, orientation="vertical")
    assert len(png) > 0
    assert png[:4] == b"\x89PNG"


def test_generate_label_compact_horizontal():
    item_id = uuid.uuid4()
    code = uuid_to_short_code(item_id)
    png = generate_label_compact(item_id, "Test Item", code, 30, 15, orientation="horizontal")
    assert len(png) > 0
    assert png[:4] == b"\x89PNG"


def test_generate_label_compact_different_sizes():
    item_id = uuid.uuid4()
    code = uuid_to_short_code(item_id)
    small = generate_label_compact(item_id, "Test Item", code, 12, 30)
    large = generate_label_compact(item_id, "Test Item", code, 20, 50)
    assert len(large) > len(small)


def test_generate_label_full_vertical():
    item_id = uuid.uuid4()
    code = uuid_to_short_code(item_id)
    png = generate_label_full(item_id, "Test Item", code, 15, 30, orientation="vertical")
    assert len(png) > 0
    assert png[:4] == b"\x89PNG"


def test_generate_label_full_horizontal():
    item_id = uuid.uuid4()
    code = uuid_to_short_code(item_id)
    png = generate_label_full(item_id, "Test Item", code, 30, 15, orientation="horizontal")
    assert len(png) > 0
    assert png[:4] == b"\x89PNG"


def test_generate_label_full_long_name():
    item_id = uuid.uuid4()
    code = uuid_to_short_code(item_id)
    long_name = "A" * 100
    png = generate_label_full(item_id, long_name, code, 15, 30)
    assert len(png) > 0
