from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenError
from app.config import get_settings
from app.db.engine import get_db
from app.dependencies import get_current_user
from app.items.service import get_item_by_id
from app.labels.service import generate_label_compact, generate_label_full
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


def _parse_size(
    size: str,
    custom_width: int,
    custom_height: int,
) -> tuple[int, int]:
    if size == "custom":
        return max(1, custom_width), max(1, custom_height)
    from app.labels.schemas import LABEL_PRESETS

    dims = LABEL_PRESETS.get(size)
    if dims is None:
        return 15, 30
    return dims


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
    html = template.render(item=item, current_user=user)
    return HTMLResponse(content=html)


@router.get("/items/{item_id}/label/preview")
async def label_preview(
    item_id: uuid.UUID,
    size: str = Query("15x30"),
    label_type: str = Query("compact"),
    orientation: str = Query("vertical"),
    custom_width: int = Query(20),
    custom_height: int = Query(50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    item = await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    w, h = _parse_size(size, custom_width, custom_height)

    if label_type == "full":
        settings = get_settings()
        png = generate_label_full(
            item.id, item.name, item.short_code, w, h,
            app_url=settings.app_url,
            orientation=orientation,
        )
    else:
        png = generate_label_compact(
            item.id, item.name, item.short_code, w, h,
            orientation=orientation,
        )

    return Response(content=png, media_type="image/png")


@router.get("/items/{item_id}/label/download")
async def label_download(
    item_id: uuid.UUID,
    size: str = Query("15x30"),
    label_type: str = Query("compact"),
    orientation: str = Query("vertical"),
    custom_width: int = Query(20),
    custom_height: int = Query(50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    item = await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    w, h = _parse_size(size, custom_width, custom_height)

    if label_type == "full":
        settings = get_settings()
        png = generate_label_full(
            item.id, item.name, item.short_code, w, h,
            app_url=settings.app_url,
            orientation=orientation,
        )
    else:
        png = generate_label_compact(
            item.id, item.name, item.short_code, w, h,
            orientation=orientation,
        )

    filename = f"label-{item.id}.png"
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
