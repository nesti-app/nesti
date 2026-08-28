from __future__ import annotations

import io
import uuid
from pathlib import PurePosixPath

from PIL import Image, ImageFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.config import get_settings
from app.media.models import ItemImage

ImageFile.LOAD_TRUNCATED_IMAGES = True

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
BLOCKED_EXTENSIONS = {".exe", ".sh", ".bat", ".cmd", ".com", ".msi", ".scr", ".pif"}


def validate_upload(filename: str, content_type: str, size_bytes: int) -> None:
    settings = get_settings()

    if size_bytes > settings.max_upload_size:
        max_mb = settings.max_upload_size // (1024 * 1024)
        raise ConflictError(f"File too large: {size_bytes} bytes (max {max_mb}MB)")

    if content_type not in ALLOWED_MIME_TYPES:
        raise ConflictError(f"Unsupported file type: {content_type}")

    ext = PurePosixPath(filename).suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        raise ConflictError(f"Blocked file extension: {ext}")


def process_image(data: bytes, content_type: str) -> dict:
    settings = get_settings()
    img = Image.open(io.BytesIO(data))

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    orig_w, orig_h = img.size

    optimized = _resize_within(
        img,
        settings.image_max_dimension,
    )
    optimized_bytes, optimized_w, optimized_h = _to_webp(optimized)

    thumb = _resize_within(img, settings.thumbnail_max_dimension)
    thumb_bytes, thumb_w, thumb_h = _to_webp(thumb)

    mime = "image/webp"

    return {
        "optimized": optimized_bytes,
        "optimized_width": optimized_w,
        "optimized_height": optimized_h,
        "thumbnail": thumb_bytes,
        "thumbnail_width": thumb_w,
        "thumbnail_height": thumb_h,
        "mime_type": mime,
        "orig_width": orig_w,
        "orig_height": orig_h,
    }


def _resize_within(img: Image.Image, max_dim: int) -> Image.Image:
    w, h = img.size
    if w <= max_dim and h <= max_dim:
        return img.copy()
    ratio = min(max_dim / w, max_dim / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    return img.resize((new_w, new_h), Image.LANCZOS)


def _to_webp(img: Image.Image) -> tuple[bytes, int, int]:
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85, method=4)
    return buf.getvalue(), img.size[0], img.size[1]


def generate_storage_paths(
    item_id: uuid.UUID, image_id: uuid.UUID | None = None,
) -> tuple[str, str]:
    folder = str(item_id)
    name = str(image_id) if image_id else str(uuid.uuid4())
    return f"{folder}/{name}-optimized.webp", f"{folder}/{name}-thumbnail.webp"


async def upload_image(
    db: AsyncSession,
    *,
    item_id: uuid.UUID,
    filename: str,
    content_type: str,
    data: bytes,
    user_id: uuid.UUID | None = None,
) -> ItemImage:
    validate_upload(filename, content_type, len(data))

    processed = process_image(data, content_type)
    image_id = uuid.uuid4()
    opt_path, thumb_path = generate_storage_paths(item_id, image_id)

    settings = get_settings()
    bucket = settings.supabase_storage_bucket

    from supabase import create_client

    client = create_client(settings.supabase_url, settings.effective_secret_key)

    client.storage.from_(bucket).upload(
        opt_path,
        processed["optimized"],
        file_options={"content-type": processed["mime_type"]},
    )
    client.storage.from_(bucket).upload(
        thumb_path,
        processed["thumbnail"],
        file_options={"content-type": processed["mime_type"]},
    )

    existing = await db.execute(select(ItemImage).where(ItemImage.item_id == item_id))
    existing_count = len(existing.scalars().all())

    is_primary = existing_count == 0

    image = ItemImage(
        item_id=item_id,
        storage_path=opt_path,
        mime_type=processed["mime_type"],
        width=processed["optimized_width"],
        height=processed["optimized_height"],
        size_bytes=len(processed["optimized"]),
        sort_order=existing_count,
        is_primary=is_primary,
        created_by=user_id,
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)
    return image


async def delete_image(db: AsyncSession, image_id: uuid.UUID) -> None:
    result = await db.execute(select(ItemImage).where(ItemImage.id == image_id))
    image = result.scalar_one_or_none()
    if image is None:
        raise NotFoundError("Image not found")

    settings = get_settings()
    bucket = settings.supabase_storage_bucket

    p = PurePosixPath(image.storage_path)
    thumb_path = str(p.parent / p.name.replace("-optimized.webp", "-thumbnail.webp"))

    from supabase import create_client

    client = create_client(settings.supabase_url, settings.effective_secret_key)

    client.storage.from_(bucket).remove([image.storage_path, thumb_path])

    was_primary = image.is_primary
    item_id = image.item_id

    await db.delete(image)
    await db.flush()

    if was_primary:
        result = await db.execute(
            select(ItemImage)
            .where(ItemImage.item_id == item_id)
            .order_by(ItemImage.sort_order)
            .limit(1)
        )
        next_image = result.scalar_one_or_none()
        if next_image:
            next_image.is_primary = True
            await db.flush()


async def set_primary_image(
    db: AsyncSession,
    image_id: uuid.UUID,
) -> ItemImage:
    result = await db.execute(select(ItemImage).where(ItemImage.id == image_id))
    image = result.scalar_one_or_none()
    if image is None:
        raise NotFoundError("Image not found")

    await db.execute(
        ItemImage.__table__.update()
        .where(ItemImage.item_id == image.item_id)
        .values(is_primary=False)
    )

    image.is_primary = True
    await db.flush()
    await db.refresh(image)
    return image


async def reorder_images(
    db: AsyncSession,
    item_id: uuid.UUID,
    image_ids: list[uuid.UUID],
) -> None:
    for idx, image_id in enumerate(image_ids):
        result = await db.execute(
            select(ItemImage).where(ItemImage.id == image_id, ItemImage.item_id == item_id)
        )
        image = result.scalar_one_or_none()
        if image:
            image.sort_order = idx
    await db.flush()


async def get_image_url(image: ItemImage) -> str:
    settings = get_settings()
    bucket = settings.supabase_storage_bucket

    from supabase import create_client

    client = create_client(settings.supabase_url, settings.effective_secret_key)

    result = client.storage.from_(bucket).create_signed_url(image.storage_path, expires_in=3600)
    return result.get("signedUrl", "")


async def get_thumbnail_url(image: ItemImage) -> str:
    settings = get_settings()
    bucket = settings.supabase_storage_bucket

    p = PurePosixPath(image.storage_path)
    thumb_path = str(p.parent / p.name.replace("-optimized.webp", "-thumbnail.webp"))

    from supabase import create_client

    client = create_client(settings.supabase_url, settings.effective_secret_key)

    result = client.storage.from_(bucket).create_signed_url(thumb_path, expires_in=3600)
    return result.get("signedUrl", "")
