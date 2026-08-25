from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.access.service import user_has_item_permission
from app.common.exceptions import ForbiddenError
from app.config import get_settings
from app.db.engine import get_db
from app.dependencies import get_current_user
from app.items.service import get_item_by_id
from app.qr.service import generate_qr_png
from app.users.models import User

router = APIRouter(tags=["qr"])


async def _check_view_permission(
    db: AsyncSession,
    user: User,
    item_id: uuid.UUID,
) -> None:
    if user.role in ("admin", "editor", "viewer"):
        return
    has = await user_has_item_permission(db, user.id, item_id, "view")
    if not has:
        raise ForbiddenError("You do not have permission to view this item's QR code")


@router.get("/items/{item_id}/qr")
async def item_qr_image(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    png_bytes = generate_qr_png(item_id)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/items/{item_id}/qr/download")
async def item_qr_download(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    png_bytes = generate_qr_png(item_id)
    filename = f"qr-{item_id}.png"
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/scan", response_class=HTMLResponse)
async def scanner_page(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    settings = get_settings()
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("qr/scanner.html")
    html = template.render(app_url=settings.app_url, current_user=user)
    return HTMLResponse(content=html)
