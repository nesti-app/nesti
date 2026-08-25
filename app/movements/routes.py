from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenError
from app.db.engine import get_db
from app.dependencies import get_current_user
from app.items.service import get_item_by_id
from app.locations.service import list_locations
from app.movements.service import get_item_movements, move_item
from app.users.models import User

router = APIRouter(tags=["movements"])


async def _check_move_permission(
    db: AsyncSession,
    user: User,
    item_id: uuid.UUID,
) -> None:
    if user.role in ("admin", "editor"):
        return
    from app.access.service import user_has_item_permission

    has = await user_has_item_permission(db, user.id, item_id, "move")
    if not has:
        raise ForbiddenError("You do not have permission to move this item")


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
        raise ForbiddenError("You do not have permission to view this item's movements")


@router.get("/items/{item_id}/move", response_class=HTMLResponse)
async def move_form(
    request: Request,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    item = await get_item_by_id(db, item_id)
    await _check_move_permission(db, user, item_id)
    locations, _ = await list_locations(db)

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("movements/_move_form.html")
    html = template.render(item=item, locations=locations)
    return HTMLResponse(content=html)


@router.post("/items/{item_id}/move")
async def move_submit(
    request: Request,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    item = await get_item_by_id(db, item_id)
    await _check_move_permission(db, user, item_id)

    form = await request.form()
    to_location_raw = form.get("to_location_id", "")
    to_location_id = uuid.UUID(str(to_location_raw)) if to_location_raw else None
    reason = str(form.get("reason", "")).strip() or None
    notes = str(form.get("notes", "")).strip() or None

    await move_item(db, item.id, to_location_id, reason, notes, user.id)
    await db.commit()

    return RedirectResponse(
        url=f"/items/{item_id}",
        status_code=303,
    )


@router.get("/items/{item_id}/movements", response_class=HTMLResponse)
async def movement_history(
    request: Request,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)

    movements, _ = await get_item_movements(db, item_id)

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("movements/_timeline.html")
    html = template.render(movements=movements)
    return HTMLResponse(content=html)
