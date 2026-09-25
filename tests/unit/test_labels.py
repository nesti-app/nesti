from __future__ import annotations

import io
import uuid

from PIL import Image, ImageChops, ImageDraw

from app.common.forms import parse_bool
from app.labels.schemas import (
    LABEL_PRESETS,
    LabelRequest,
    LabelSize,
    parse_label_size,
)
from app.labels.service import (
    _code_inset,
    _load_font,
    _wrap_text,
    generate_label_compact,
    generate_label_full,
    mm_to_px,
)
from app.qr.service import uuid_to_short_code


def test_mm_to_px():
    assert mm_to_px(25, 203) == 199
    assert mm_to_px(25.4, 203) == 203
    assert mm_to_px(1, 203) == 7


def test_code_inset_scales_with_font_size():
    assert _code_inset(6) == 4
    assert _code_inset(10) == 4
    assert _code_inset(14) == 5
    assert _code_inset(18) == 6


def test_parse_label_size_helpers():
    assert parse_label_size("30x15", 1, 1) == (30, 15)
    assert parse_label_size("custom", 12, 34) == (12, 34)
    assert parse_label_size("nope", 1, 1) == (15, 30)


def test_parse_bool():
    assert parse_bool("on") is True
    assert parse_bool("1") is True
    assert parse_bool("true") is True
    assert parse_bool(True) is True
    assert parse_bool("0") is False
    assert parse_bool(None) is False


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


def test_wrap_text_multiple_lines():
    draw = ImageDraw.Draw(Image.new("RGB", (400, 200)))
    font = _load_font(12)
    lines = _wrap_text(draw, "Alpha Beta Gamma Delta Epsilon", font, max_w=150)
    assert 2 <= len(lines) <= 3
    assert " ".join(lines) == "Alpha Beta Gamma Delta Epsilon"


def test_wrap_text_single_long_word_hard_breaks():
    draw = ImageDraw.Draw(Image.new("RGB", (200, 200)))
    font = _load_font(12)
    lines = _wrap_text(draw, "A" * 50, font, max_w=40, max_lines=3)
    assert len(lines) <= 3
    assert all(len(line) <= 50 for line in lines)


def test_wrap_text_truncates_with_ellipsis_when_too_long():
    draw = ImageDraw.Draw(Image.new("RGB", (200, 200)))
    font = _load_font(12)
    lines = _wrap_text(
        draw, "One Two Three Four Five Six Seven Eight Nine", font, max_w=40, max_lines=3
    )
    assert len(lines) == 3
    assert lines[-1].endswith("…")


def test_generate_label_full_with_custom_font_sizes():
    item_id = uuid.uuid4()
    code = uuid_to_short_code(item_id)
    name = "Lithium Iron Phosphate Battery 18650"
    small = generate_label_full(
        item_id, name, code, 30, 15,
        orientation="horizontal",
        name_font_size=10, code_font_size=8,
    )
    large = generate_label_full(
        item_id, name, code, 30, 15,
        orientation="horizontal",
        name_font_size=22, code_font_size=16,
    )
    assert small != large


def test_generate_label_compact_with_custom_font_sizes():
    item_id = uuid.uuid4()
    code = uuid_to_short_code(item_id)
    png = generate_label_compact(
        item_id, "Test Item", code, 15, 30,
        name_font_size=20, code_font_size=14,
    )
    assert len(png) > 0


def test_generate_label_full_default_fonts_are_14_and_10():
    item_id = uuid.uuid4()
    code = uuid_to_short_code(item_id)
    name = "Network Switch Rack Unit"
    default = generate_label_full(item_id, name, code, 30, 15, orientation="horizontal")
    explicit = generate_label_full(
        item_id, name, code, 30, 15,
        orientation="horizontal", name_font_size=14, code_font_size=10,
    )
    assert default == explicit


def test_generate_label_honors_wrap_settings():
    item_id = uuid.uuid4()
    name = "One Two Three Four Five Six"
    one_line = generate_label_full(
        item_id, name, "CODE", 30, 15, orientation="horizontal", max_name_lines=1
    )
    many_lines = generate_label_full(
        item_id, name, "CODE", 30, 15, orientation="horizontal", max_name_lines=4
    )
    assert one_line != many_lines

    by_words = generate_label_full(
        item_id, name, "CODE", 30, 15, orientation="horizontal", wrap_by_words=True
    )
    by_chars = generate_label_full(
        item_id, name, "CODE", 30, 15, orientation="horizontal", wrap_by_words=False
    )
    assert by_words != by_chars


def test_wrap_text_supports_four_lines():
    draw = ImageDraw.Draw(Image.new("RGB", (400, 200)))
    font = _load_font(14)
    lines = _wrap_text(draw, "One Two Three Four Five Six Seven", font, max_w=55)
    assert 2 <= len(lines) <= 4
    assert " ".join(lines).startswith("One")


def test_wrap_text_max_lines_is_respected():
    draw = ImageDraw.Draw(Image.new("RGB", (400, 200)))
    font = _load_font(14)
    lines = _wrap_text(draw, "One Two Three Four Five Six Seven", font, max_w=55, max_lines=2)
    assert len(lines) == 2
    assert lines[-1].endswith("…")


def test_wrap_text_by_chars_breaks_within_words():
    draw = ImageDraw.Draw(Image.new("RGB", (400, 200)))
    font = _load_font(12)
    lines = _wrap_text(draw, "ABCDEFGHIJKLMNOP", font, max_w=30, by_words=False)
    assert len(lines) >= 2
    assert all(draw.textbbox((0, 0), line, font=font)[2] <= 30 for line in lines)


def test_wrap_text_word_mode_does_not_break_short_words():
    draw = ImageDraw.Draw(Image.new("RGB", (400, 200)))
    font = _load_font(12)
    text = "Alpha Beta Gamma Delta"
    lines = _wrap_text(draw, text, font, max_w=50, max_lines=10, by_words=True)
    assert " ".join(lines) == text


def _code_bbox(label_a: bytes, label_b: bytes) -> tuple[int, int, int, int] | None:
    img_a = Image.open(io.BytesIO(label_a)).convert("RGB")
    img_b = Image.open(io.BytesIO(label_b)).convert("RGB")
    return ImageChops.difference(img_a, img_b).convert("L").getbbox()


def test_generate_label_full_code_is_bottom_right_horizontal():
    item_id = uuid.uuid4()
    common = ("Li-Ion Cell", 30, 15)
    a = generate_label_full(
        item_id, common[0], "AAAA", common[1], common[2], orientation="horizontal"
    )
    b = generate_label_full(
        item_id, common[0], "BBBB", common[1], common[2], orientation="horizontal"
    )
    bbox = _code_bbox(a, b)
    assert bbox is not None
    img = Image.open(io.BytesIO(a))
    assert bbox[0] > img.width // 2
    assert bbox[1] > img.height // 2


def test_generate_label_full_code_is_bottom_right_vertical():
    item_id = uuid.uuid4()
    a = generate_label_full(item_id, "Li-Ion Cell", "AAAA", 15, 30, orientation="vertical")
    b = generate_label_full(item_id, "Li-Ion Cell", "BBBB", 15, 30, orientation="vertical")
    bbox = _code_bbox(a, b)
    assert bbox is not None
    img = Image.open(io.BytesIO(a))
    assert bbox[0] > img.width // 2
    assert bbox[1] > img.height // 2


def test_generate_label_compact_code_is_bottom_right():
    item_id = uuid.uuid4()
    a = generate_label_compact(item_id, "Li-Ion Cell", "AAAA", 30, 15, orientation="horizontal")
    b = generate_label_compact(item_id, "Li-Ion Cell", "BBBB", 30, 15, orientation="horizontal")
    bbox = _code_bbox(a, b)
    assert bbox is not None
    img = Image.open(io.BytesIO(a))
    assert bbox[0] > img.width // 2
    assert bbox[1] > img.height // 2
