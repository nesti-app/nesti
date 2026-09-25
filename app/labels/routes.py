from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenError
from app.common.forms import parse_bool
from app.config import get_settings
from app.db.engine import get_db
from app.dependencies import get_current_user
from app.items.service import get_item_by_id
from app.labels.service import generate_label_compact, generate_label_full
from app.labels.settings import get_label_settings
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
    from app.labels.schemas import parse_label_size

    return parse_label_size(size, custom_width, custom_height)


@router.get("/items/{item_id}/label", response_class=HTMLResponse)
async def label_dialog(
    request: Request,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    item = await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    defaults = await get_label_settings(db)

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("labels/_dialog.html")
    html = template.render(item=item, current_user=user, defaults=defaults)
    return HTMLResponse(content=html)


@router.get("/items/{item_id}/label/preview")
async def label_preview(
    item_id: uuid.UUID,
    size: str = Query("15x30"),
    label_type: str = Query("compact"),
    orientation: str = Query("vertical"),
    custom_width: int = Query(20),
    custom_height: int = Query(50),
    name_font_size: int | None = Query(None),
    code_font_size: int | None = Query(None),
    max_name_lines: int | None = Query(None),
    wrap_by_words: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    item = await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    w, h = _parse_size(size, custom_width, custom_height)
    defaults = await get_label_settings(db)
    lines = max_name_lines or defaults.max_name_lines
    by_words = defaults.wrap_by_words if wrap_by_words is None else parse_bool(wrap_by_words)

    if label_type == "full":
        settings = get_settings()
        png = generate_label_full(
            item.id, item.name, item.short_code, w, h,
            app_url=settings.app_url,
            orientation=orientation,
            name_font_size=name_font_size,
            code_font_size=code_font_size,
            max_name_lines=lines,
            wrap_by_words=by_words,
        )
    else:
        png = generate_label_compact(
            item.id, item.name, item.short_code, w, h,
            orientation=orientation,
            name_font_size=name_font_size,
            code_font_size=code_font_size,
            max_name_lines=lines,
            wrap_by_words=by_words,
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
    name_font_size: int | None = Query(None),
    code_font_size: int | None = Query(None),
    max_name_lines: int | None = Query(None),
    wrap_by_words: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    item = await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    w, h = _parse_size(size, custom_width, custom_height)
    defaults = await get_label_settings(db)
    lines = max_name_lines or defaults.max_name_lines
    by_words = defaults.wrap_by_words if wrap_by_words is None else parse_bool(wrap_by_words)

    if label_type == "full":
        settings = get_settings()
        png = generate_label_full(
            item.id, item.name, item.short_code, w, h,
            app_url=settings.app_url,
            orientation=orientation,
            name_font_size=name_font_size,
            code_font_size=code_font_size,
            max_name_lines=lines,
            wrap_by_words=by_words,
        )
    else:
        png = generate_label_compact(
            item.id, item.name, item.short_code, w, h,
            orientation=orientation,
            name_font_size=name_font_size,
            code_font_size=code_font_size,
            max_name_lines=lines,
            wrap_by_words=by_words,
        )

    filename = f"label-{item.id}.png"
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
