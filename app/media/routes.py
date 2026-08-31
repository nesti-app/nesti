from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.access.service import user_has_item_permission
from app.common.exceptions import ForbiddenError
from app.db.engine import get_db
from app.dependencies import get_current_user
from app.media.models import ItemImage
from app.media.service import (
    delete_image,
    reorder_images,
    set_primary_image,
    upload_image,
)
from app.users.models import User

router = APIRouter(prefix="/items/{item_id}/images", tags=["images"])


async def _check_manage_images(
    db: AsyncSession,
    user: User,
    item_id: uuid.UUID,
) -> None:
    if user.role in ("admin", "editor"):
        return
    has = await user_has_item_permission(db, user.id, item_id, "manage_images")
    if not has:
        raise ForbiddenError("You do not have permission to manage images")


@router.post("")
async def upload_item_image(
    item_id: uuid.UUID,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await _check_manage_images(db, user, item_id)

    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    await upload_image(
        db,
        item_id=item_id,
        filename=file.filename or "upload",
        content_type=content_type,
        data=content,
        user_id=user.id,
    )

    return RedirectResponse(url=f"/items/{item_id}", status_code=303)


@router.post("/{image_id}/delete")
async def delete_item_image(
    item_id: uuid.UUID,
    image_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await _check_manage_images(db, user, item_id)
    await delete_image(db, image_id)
    return RedirectResponse(url=f"/items/{item_id}", status_code=303)


@router.post("/{image_id}/primary")
async def set_item_image_primary(
    item_id: uuid.UUID,
    image_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await _check_manage_images(db, user, item_id)
    await set_primary_image(db, image_id)
    return RedirectResponse(url=f"/items/{item_id}", status_code=303)


@router.post("/reorder")
async def reorder_item_images(
    item_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await _check_manage_images(db, user, item_id)

    form = await request.form()
    image_ids_str = form.getlist("image_order")
    image_ids = []
    for id_str in image_ids_str:
        try:
            image_ids.append(uuid.UUID(id_str))
        except ValueError:
            continue

    await reorder_images(db, item_id, image_ids)
    return RedirectResponse(url=f"/items/{item_id}", status_code=303)


@router.get("/{image_id}/file")
async def serve_image_file(
    item_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    from sqlalchemy import select

    from app.media.storage import get_storage_backend

    result = await db.execute(
        select(ItemImage).where(ItemImage.id == image_id, ItemImage.item_id == item_id)
    )
    image = result.scalar_one_or_none()
    if image is None:
        return Response(status_code=404)

    try:
        data = await get_storage_backend().download(image.storage_path)
        return Response(content=data, media_type=image.mime_type)
    except Exception:
        return Response(status_code=404)
