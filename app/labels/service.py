from __future__ import annotations

import io
import uuid

from PIL import Image, ImageDraw, ImageFont

from app.qr.service import generate_qr_png_compact


def mm_to_px(mm: int, dpi: int) -> int:
    return int(mm / 25.4 * dpi)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _truncate_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_w: int,
) -> str:
    name = text
    bbox = draw.textbbox((0, 0), name, font=font)
    while bbox[2] - bbox[0] > max_w and len(name) > 3:
        name = name[:-1]
        bbox = draw.textbbox((0, 0), name + "...", font=font)
    if len(name) < len(text):
        name += "..."
    return name


def generate_label_compact(
    item_id: uuid.UUID,
    item_name: str,
    short_code: str,
    width_mm: int,
    height_mm: int,
    dpi: int = 203,
    orientation: str = "vertical",
) -> bytes:
    w_px = mm_to_px(width_mm, dpi)
    h_px = mm_to_px(height_mm, dpi)

    label = Image.new("RGB", (w_px, h_px), "white")
    draw = ImageDraw.Draw(label)

    qr_bytes = generate_qr_png_compact(item_id)
    qr_img = Image.open(io.BytesIO(qr_bytes))

    if orientation == "horizontal":
        qr_size = min(w_px // 2 - 4, h_px - 4)
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_x = 2
        qr_y = (h_px - qr_size) // 2
        label.paste(qr_img, (qr_x, qr_y))

        text_x = qr_x + qr_size + 4
        text_max_w = w_px - text_x - 2

        name_font = _load_font(max(8, min(12, qr_size // 4)))
        name = _truncate_text(draw, item_name, name_font, text_max_w)
        name_bbox = draw.textbbox((0, 0), name, font=name_font)
        name_h = name_bbox[3] - name_bbox[1]

        code_font = _load_font(max(7, min(10, qr_size // 5)))
        code_bbox = draw.textbbox((0, 0), short_code, font=code_font)
        code_h = code_bbox[3] - code_bbox[1]

        total_h = name_h + 2 + code_h
        start_y = qr_y + (qr_size - total_h) // 2

        if start_y + total_h <= qr_y + qr_size:
            draw.text((text_x, start_y), name, fill="black", font=name_font)
            draw.text((text_x, start_y + name_h + 2), short_code, fill="gray", font=code_font)
    else:
        qr_size = min(w_px, h_px) - 8
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_x = (w_px - qr_size) // 2
        qr_y = 2
        label.paste(qr_img, (qr_x, qr_y))

        name_font = _load_font(10)
        name = _truncate_text(draw, item_name, name_font, w_px - 4)
        name_bbox = draw.textbbox((0, 0), name, font=name_font)
        name_w = name_bbox[2] - name_bbox[0]
        name_x = (w_px - name_w) // 2
        name_y = qr_y + qr_size + 2

        if name_y + 12 <= h_px:
            draw.text((name_x, name_y), name, fill="black", font=name_font)

        code_font = _load_font(8)
        code_bbox = draw.textbbox((0, 0), short_code, font=code_font)
        code_w = code_bbox[2] - code_bbox[0]
        code_x = (w_px - code_w) // 2
        code_y = name_y + 12

        if code_y + 10 <= h_px:
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
    qr_img = Image.open(io.BytesIO(qr_bytes))

    if orientation == "horizontal":
        qr_size = min(w_px // 2 - 4, h_px - 8)
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_x = 2
        qr_y = (h_px - qr_size) // 2
        label.paste(qr_img, (qr_x, qr_y))

        text_x = qr_x + qr_size + 4
        text_max_w = w_px - text_x - 2

        name_font = _load_font(10)
        name = _truncate_text(draw, item_name, name_font, text_max_w)
        name_bbox = draw.textbbox((0, 0), name, font=name_font)

        code_font = _load_font(8)
        code_bbox = draw.textbbox((0, 0), short_code, font=code_font)

        total_h = (name_bbox[3] - name_bbox[1]) + 2 + (code_bbox[3] - code_bbox[1])
        start_y = (h_px - total_h) // 2

        if start_y + total_h <= h_px:
            draw.text((text_x, start_y), name, fill="black", font=name_font)
            name_h = name_bbox[3] - name_bbox[1]
            draw.text(
                (text_x, start_y + name_h + 2),
                short_code,
                fill="gray",
                font=code_font,
            )
    else:
        qr_size = min(w_px, h_px) // 2
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_x = (w_px - qr_size) // 2
        qr_y = 4
        label.paste(qr_img, (qr_x, qr_y))

        text_y = qr_y + qr_size + 4
        max_text_w = w_px - 8

        name_font = _load_font(12)
        name = _truncate_text(draw, item_name, name_font, max_text_w)
        text_bbox = draw.textbbox((0, 0), name, font=name_font)
        text_w = text_bbox[2] - text_bbox[0]
        text_x = (w_px - text_w) // 2

        if text_y + 16 <= h_px:
            draw.text((text_x, text_y), name, fill="black", font=name_font)

        code_font = _load_font(9)
        code_bbox = draw.textbbox((0, 0), short_code, font=code_font)
        code_w = code_bbox[2] - code_bbox[0]
        code_x = (w_px - code_w) // 2
        code_y = text_y + 16

        if code_y + 12 <= h_px:
            draw.text((code_x, code_y), short_code, fill="gray", font=code_font)

    buf = io.BytesIO()
    label.save(buf, format="PNG", dpi=(dpi, dpi))
    return buf.getvalue()
