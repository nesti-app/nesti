from __future__ import annotations

import base64
import io
import uuid

import qrcode

_SHORT_CODE_CHARS = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz"


def uuid_to_short_code(item_id: uuid.UUID) -> str:
    raw = item_id.bytes[:4]
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def short_code_to_uuid_prefix(code: str) -> str:
    padded = code + "=" * (-len(code) % 4)
    raw = base64.urlsafe_b64decode(padded)
    return raw.hex()


def build_full_url(item_id: uuid.UUID, app_url: str) -> str:
    return f"{app_url.rstrip('/')}/items/{item_id}"


def build_short_url(short_code: str, app_url: str) -> str:
    return f"{app_url.rstrip('/')}/s/{short_code}"


def generate_qr_png_compact(item_id: uuid.UUID) -> bytes:
    code = uuid_to_short_code(item_id)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(code)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr_png_full(item_id: uuid.UUID, app_url: str) -> bytes:
    url = build_full_url(item_id, app_url)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr_png_short(short_code: str, app_url: str) -> bytes:
    url = build_short_url(short_code, app_url)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr_svg_compact(item_id: uuid.UUID) -> bytes:
    code = uuid_to_short_code(item_id)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(code)
    qr.make(fit=True)

    from qrcode.image.svg import SvgPathImage

    img = qr.make_image(image_factory=SvgPathImage)

    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue()


def generate_qr_svg_full(item_id: uuid.UUID, app_url: str) -> bytes:
    url = build_full_url(item_id, app_url)

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
