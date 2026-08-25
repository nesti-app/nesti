from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenError
from app.db.engine import get_db
from app.dependencies import get_current_user
from app.items.service import get_item_by_id
from app.labels.service import generate_label_png
from app.users.models import User

router = APIRouter(tags=["labels"])


async def _check_view_permission(
    db: AsyncSession,
    user: User,
    item_id: uuid.UUID,
) -> None:
    if user.role in ("admin", "editor", "viewer"):
        return
    from app.access.service import user_has_item_permission

    has = await user_has_item_permission(db, user.id, item_id, "view")
    if not has:
        raise ForbiddenError("You do not have permission to view this item's label")


@router.get("/items/{item_id}/label", response_class=HTMLResponse)
async def label_dialog(
    request: Request,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    item = await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("labels/_dialog.html")
    html = template.render(item=item)
    return HTMLResponse(content=html)


@router.get("/items/{item_id}/label/preview")
async def label_preview(
    item_id: uuid.UUID,
    size: str = Query("15x30"),
    custom_width: int = Query(20),
    custom_height: int = Query(50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    item = await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    if size == "custom":
        w, h = max(1, custom_width), max(1, custom_height)
    else:
        from app.labels.schemas import LABEL_PRESETS

        dims = LABEL_PRESETS.get(size)
        if dims is None:
            w, h = 15, 30
        else:
            w, h = dims

    png = generate_label_png(item.id, item.name, w, h)
    return Response(content=png, media_type="image/png")


@router.get("/items/{item_id}/label/download")
async def label_download(
    item_id: uuid.UUID,
    size: str = Query("15x30"),
    custom_width: int = Query(20),
    custom_height: int = Query(50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    item = await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    if size == "custom":
        w, h = max(1, custom_width), max(1, custom_height)
    else:
        from app.labels.schemas import LABEL_PRESETS

        dims = LABEL_PRESETS.get(size)
        if dims is None:
            w, h = 15, 30
        else:
            w, h = dims

    png = generate_label_png(item.id, item.name, w, h)
    filename = f"label-{item.id}.png"
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
