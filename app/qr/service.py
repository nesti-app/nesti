from __future__ import annotations

import io
import uuid

import qrcode

from app.config import get_settings


def build_qr_url(item_id: uuid.UUID) -> str:
    settings = get_settings()
    return f"{settings.app_url.rstrip('/')}/items/{item_id}"


def generate_qr_png(item_id: uuid.UUID) -> bytes:
    url = build_qr_url(item_id)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr_svg(item_id: uuid.UUID) -> bytes:
    url = build_qr_url(item_id)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    from qrcode.image.svg import SvgPathImage

    img = qr.make_image(image_factory=SvgPathImage)

    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue()
