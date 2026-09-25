from __future__ import annotations

import io
import uuid

from PIL import Image, ImageDraw, ImageFont

from app.labels.schemas import (
    DEFAULT_CODE_FONT_SIZE,
    DEFAULT_MAX_NAME_LINES,
    DEFAULT_NAME_FONT_SIZE,
)
from app.qr.service import generate_qr_png_compact

Font = ImageFont.FreeTypeFont | ImageFont.ImageFont


def mm_to_px(mm: int, dpi: int) -> int:
    return int(mm / 25.4 * dpi)


_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
)


def _load_font(size: int) -> Font:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _line_height(draw: ImageDraw.ImageDraw, font: Font) -> int:
    bbox = draw.textbbox((0, 0), "Áég", font=font)
    return max(8, int(bbox[3] - bbox[1]))


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: Font,
    max_w: int,
    max_lines: int = DEFAULT_MAX_NAME_LINES,
    by_words: bool = True,
) -> list[str]:
    """Wrap text into at most ``max_lines`` lines; cut off the tail with an ellipsis.

    When ``by_words`` is true, lines break at spaces (hard-breaking words that
    are wider than ``max_w``); otherwise every character is a break candidate.
    """
    tokens = text.split() if by_words else list(text)
    if not tokens:
        return [""]

    joiner = " " if by_words else ""
    lines: list[str] = []
    current = ""
    truncated = False

    for token in tokens:
        candidate = f"{current}{joiner}{token}" if current else token
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_w:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = token
        else:
            piece = ""
            for ch in token:
                if draw.textbbox((0, 0), piece + ch, font=font)[2] <= max_w:
                    piece += ch
                else:
                    lines.append(piece)
                    piece = ch
                    if len(lines) >= max_lines:
                        truncated = True
                        break
            current = piece

        if len(lines) >= max_lines:
            truncated = True
            break

    if current:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True

    if truncated and lines:
        last = lines[-1]
        while last and draw.textbbox((0, 0), last + "…", font=font)[2] > max_w:
            last = last[:-1]
        lines[-1] = last + "…"

    return lines


def _code_inset(font_size: int) -> int:
    """Bottom/right inset for the code, derived from its font size.

    A small base gap keeps the code off the edge; larger fonts get a
    proportionally bigger margin.
    """
    return 4 + max(0, (font_size - DEFAULT_CODE_FONT_SIZE) // 4)


def _code_position(
    draw: ImageDraw.ImageDraw,
    w_px: int,
    h_px: int,
    short_code: str,
    font: Font,
    font_size: int,
) -> tuple[int, int]:
    """Return the top-left position anchoring the code in the bottom-right corner."""
    bbox = draw.textbbox((0, 0), short_code, font=font)
    inset = _code_inset(font_size)
    return (
        max(0, int(w_px - inset - bbox[2])),
        max(0, int(h_px - inset - bbox[3])),
    )


def generate_label_compact(
    item_id: uuid.UUID,
    item_name: str,
    short_code: str,
    width_mm: int,
    height_mm: int,
    dpi: int = 203,
    orientation: str = "vertical",
    name_font_size: int | None = None,
    code_font_size: int | None = None,
    max_name_lines: int | None = None,
    wrap_by_words: bool = True,
) -> bytes:
    w_px = mm_to_px(width_mm, dpi)
    h_px = mm_to_px(height_mm, dpi)

    label = Image.new("RGB", (w_px, h_px), "white")
    draw = ImageDraw.Draw(label)

    qr_bytes = generate_qr_png_compact(item_id)
    qr_img: Image.Image = Image.open(io.BytesIO(qr_bytes))

    margin = 2
    code_size = code_font_size or DEFAULT_CODE_FONT_SIZE
    max_lines = max_name_lines or DEFAULT_MAX_NAME_LINES
    name_font = _load_font(name_font_size or DEFAULT_NAME_FONT_SIZE)
    code_font = _load_font(code_size)
    name_h = _line_height(draw, name_font)
    code_x, code_y = _code_position(draw, w_px, h_px, short_code, code_font, code_size)

    if orientation == "horizontal":
        qr_size = min(w_px // 2 - 4, h_px - 4)
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_x = margin
        qr_y = (h_px - qr_size) // 2
        label.paste(qr_img, (qr_x, qr_y))

        name_x = qr_x + qr_size + 4
        name_max_w = max(1, w_px - margin - name_x)
        name_lines = _wrap_text(
            draw, item_name, name_font, name_max_w, max_lines=max_lines, by_words=wrap_by_words
        )
        name_area_top = margin
        name_area_bottom = code_y - 2
        total_name_h = name_h * len(name_lines)
        start_y = name_area_top + max(0, (name_area_bottom - name_area_top - total_name_h) // 2)

        for i, line in enumerate(name_lines):
            draw.text((name_x, start_y + i * name_h), line, fill="black", font=name_font)
    else:
        qr_size = min(w_px, h_px) - 8
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_x = (w_px - qr_size) // 2
        qr_y = margin
        label.paste(qr_img, (qr_x, qr_y))

        name_max_w = max(1, w_px - 2 * margin)
        name_lines = _wrap_text(
            draw, item_name, name_font, name_max_w, max_lines=max_lines, by_words=wrap_by_words
        )
        name_area_top = qr_y + qr_size + 2
        name_area_bottom = code_y - 2
        total_name_h = name_h * len(name_lines)
        start_y = name_area_top + max(0, (name_area_bottom - name_area_top - total_name_h) // 2)

        for i, line in enumerate(name_lines):
            line_bbox = draw.textbbox((0, 0), line, font=name_font)
            line_w = line_bbox[2] - line_bbox[0]
            line_x = max(margin, (w_px - line_w) // 2)
            draw.text((line_x, start_y + i * name_h), line, fill="black", font=name_font)

    draw.text((code_x, code_y), short_code, fill="gray", font=code_font)

    buf = io.BytesIO()
    label.save(buf, format="PNG", dpi=(dpi, dpi))
    return buf.getvalue()


def generate_label_full(
    item_id: uuid.UUID,
    item_name: str,
    short_code: str,
    width_mm: int,
    height_mm: int,
    dpi: int = 203,
    app_url: str = "",
    orientation: str = "vertical",
    name_font_size: int | None = None,
    code_font_size: int | None = None,
    max_name_lines: int | None = None,
    wrap_by_words: bool = True,
) -> bytes:
    w_px = mm_to_px(width_mm, dpi)
    h_px = mm_to_px(height_mm, dpi)

    label = Image.new("RGB", (w_px, h_px), "white")
    draw = ImageDraw.Draw(label)

    if app_url:
        from app.qr.service import generate_qr_png_short
        qr_bytes = generate_qr_png_short(short_code, app_url)
    else:
        qr_bytes = generate_qr_png_compact(item_id)
    qr_img: Image.Image = Image.open(io.BytesIO(qr_bytes))

    margin = 2
    code_size = code_font_size or DEFAULT_CODE_FONT_SIZE
    max_lines = max_name_lines or DEFAULT_MAX_NAME_LINES
    name_font = _load_font(name_font_size or DEFAULT_NAME_FONT_SIZE)
    code_font = _load_font(code_size)
    name_h = _line_height(draw, name_font)
    code_x, code_y = _code_position(draw, w_px, h_px, short_code, code_font, code_size)

    if orientation == "horizontal":
        qr_size = min(w_px // 2 - 4, h_px - 8)
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_x = margin
        qr_y = (h_px - qr_size) // 2
        label.paste(qr_img, (qr_x, qr_y))

        name_x = qr_x + qr_size + 4
        name_max_w = max(1, w_px - margin - name_x)
        name_lines = _wrap_text(
            draw, item_name, name_font, name_max_w, max_lines=max_lines, by_words=wrap_by_words
        )
        name_area_top = margin
        name_area_bottom = code_y - 2
        total_name_h = name_h * len(name_lines)
        start_y = name_area_top + max(0, (name_area_bottom - name_area_top - total_name_h) // 2)

        for i, line in enumerate(name_lines):
            draw.text((name_x, start_y + i * name_h), line, fill="black", font=name_font)
    else:
        qr_size = min(w_px, h_px) // 2
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_x = (w_px - qr_size) // 2
        qr_y = margin
        label.paste(qr_img, (qr_x, qr_y))

        name_max_w = max(1, w_px - 2 * margin)
        name_lines = _wrap_text(
            draw, item_name, name_font, name_max_w, max_lines=max_lines, by_words=wrap_by_words
        )
        name_area_top = qr_y + qr_size + 2
        name_area_bottom = code_y - 2
        total_name_h = name_h * len(name_lines)
        start_y = name_area_top + max(0, (name_area_bottom - name_area_top - total_name_h) // 2)

        for i, line in enumerate(name_lines):
            line_bbox = draw.textbbox((0, 0), line, font=name_font)
            line_w = line_bbox[2] - line_bbox[0]
            line_x = max(margin, (w_px - line_w) // 2)
            draw.text((line_x, start_y + i * name_h), line, fill="black", font=name_font)

    draw.text((code_x, code_y), short_code, fill="gray", font=code_font)

    buf = io.BytesIO()
    label.save(buf, format="PNG", dpi=(dpi, dpi))
    return buf.getvalue()
