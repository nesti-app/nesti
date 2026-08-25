from __future__ import annotations

import io
import uuid

from PIL import Image, ImageDraw, ImageFont

from app.qr.service import generate_qr_png


def mm_to_px(mm: int, dpi: int) -> int:
    return int(mm / 25.4 * dpi)


def generate_label_png(
    item_id: uuid.UUID,
    item_name: str,
    width_mm: int,
    height_mm: int,
    dpi: int = 203,
) -> bytes:
    w_px = mm_to_px(width_mm, dpi)
    h_px = mm_to_px(height_mm, dpi)

    label = Image.new("RGB", (w_px, h_px), "white")
    draw = ImageDraw.Draw(label)

    qr_size = min(w_px, h_px) // 2
    qr_bytes = generate_qr_png(item_id)
    qr_img = Image.open(io.BytesIO(qr_bytes)).resize(
        (qr_size, qr_size), Image.Resampling.LANCZOS
    )

    qr_x = (w_px - qr_size) // 2
    qr_y = 4
    label.paste(qr_img, (qr_x, qr_y))

    text_y = qr_y + qr_size + 4

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except OSError:
        font = ImageFont.load_default()

    max_text_w = w_px - 8
    name = item_name
    bbox = draw.textbbox((0, 0), name, font=font)
    while bbox[2] - bbox[0] > max_text_w and len(name) > 3:
        name = name[:-1]
        bbox = draw.textbbox((0, 0), name + "...", font=font)

    if len(name) < len(item_name):
        name += "..."

    text_bbox = draw.textbbox((0, 0), name, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_x = (w_px - text_w) // 2

    if text_y + 16 <= h_px:
        draw.text((text_x, text_y), name, fill="black", font=font)

    short_id = str(item_id)[:8]
    id_bbox = draw.textbbox((0, 0), short_id, font=font)
    id_w = id_bbox[2] - id_bbox[0]
    id_x = (w_px - id_w) // 2
    id_y = text_y + 16

    if id_y + 12 <= h_px:
        try:
            small_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9
            )
        except OSError:
            small_font = ImageFont.load_default()
        draw.text((id_x, id_y), short_id, fill="gray", font=small_font)

    buf = io.BytesIO()
    label.save(buf, format="PNG", dpi=(dpi, dpi))
    return buf.getvalue()
