from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.forms import parse_bool
from app.config import get_settings
from app.db.engine import get_db
from app.dependencies import require_admin
from app.labels.schemas import (
    LABEL_PRESETS,
    LabelSettingsData,
    parse_label_size,
)
from app.labels.service import generate_label_compact, generate_label_full
from app.labels.settings import get_label_settings, save_label_settings
from app.users.models import User

DUMMY_ITEM_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
DUMMY_NAME = "Приклад назви предмета"
DUMMY_CODE = "A7F3Z2"

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("", response_class=HTMLResponse)
async def admin_index(
    request: Request,
    current_user: User = Depends(require_admin),
) -> HTMLResponse:
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("admin/index.html")
    html = template.render(current_user=current_user)
    return HTMLResponse(content=html)


@router.get("/label-settings", response_class=HTMLResponse)
async def label_settings_page(
    request: Request,
    saved: int = 0,
    error: str | None = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    settings = await get_label_settings(db)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("admin/label_settings.html")
    html = template.render(
        current_user=current_user,
        settings=settings,
        sizes=[
            {"value": key, "label": f"{w} × {h} мм"}  # noqa: RUF001
            for key, (w, h) in LABEL_PRESETS.items()
        ],
        dummy_name=DUMMY_NAME,
        dummy_code=DUMMY_CODE,
        saved=bool(saved),
        error=error,
    )
    return HTMLResponse(content=html)


@router.post("/label-settings")
async def label_settings_save(
    label_type: str = Form("full"),
    orientation: str = Form("horizontal"),
    size: str = Form("30x15"),
    custom_width: int = Form(30),
    custom_height: int = Form(15),
    name_font_size: int = Form(14),
    code_font_size: int = Form(10),
    max_name_lines: int = Form(4),
    wrap_by_words: str | None = Form(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        data = LabelSettingsData.from_form(
            label_type=label_type,
            orientation=orientation,
            size=size,
            custom_width=custom_width,
            custom_height=custom_height,
            name_font_size=name_font_size,
            code_font_size=code_font_size,
            max_name_lines=max_name_lines,
            wrap_by_words=wrap_by_words,
        )
    except ValidationError as exc:
        message = exc.errors()[0].get("msg", "invalid")
        return RedirectResponse(
            url=f"/admin/label-settings?error={message}",
            status_code=303,
        )

    await save_label_settings(db, data)
    return RedirectResponse(url="/admin/label-settings?saved=1", status_code=303)


@router.get("/label-settings/preview")
async def label_settings_preview(
    label_type: str = Query("full"),
    orientation: str = Query("horizontal"),
    size: str = Query("30x15"),
    custom_width: int = Query(30),
    custom_height: int = Query(15),
    name_font_size: int = Query(14),
    code_font_size: int = Query(10),
    max_name_lines: int = Query(4),
    wrap_by_words: str | None = Query("1"),
    name: str = Query(DUMMY_NAME),
    code: str = Query(DUMMY_CODE),
    current_user: User = Depends(require_admin),
) -> Response:
    w, h = parse_label_size(size, custom_width, custom_height)
    by_words = parse_bool(wrap_by_words)
    if label_type == "compact":
        png = generate_label_compact(
            DUMMY_ITEM_ID, name, code, w, h,
            orientation=orientation,
            name_font_size=name_font_size,
            code_font_size=code_font_size,
            max_name_lines=max_name_lines,
            wrap_by_words=by_words,
        )
    else:
        png = generate_label_full(
            DUMMY_ITEM_ID, name, code, w, h,
            app_url=get_settings().app_url,
            orientation=orientation,
            name_font_size=name_font_size,
            code_font_size=code_font_size,
            max_name_lines=max_name_lines,
            wrap_by_words=by_words,
        )
    return Response(content=png, media_type="image/png")
