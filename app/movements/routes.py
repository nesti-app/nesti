from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenError, NotFoundError
from app.db.engine import get_db
from app.dependencies import get_current_user
from app.items.service import get_item_by_id
from app.movements.service import delete_movement, get_item_movements, get_movement_by_id
from app.users.models import User

router = APIRouter(tags=["movements"])


async def _check_edit_permission(
    db: AsyncSession,
    user: User,
    item_id: uuid.UUID,
) -> None:
    if user.role in ("admin", "editor"):
        return
    from app.access.service import user_has_item_permission

    has = await user_has_item_permission(db, user.id, item_id, "edit")
    if not has:
        raise ForbiddenError("You do not have permission to edit this item's movements")


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


@router.post("/items/{item_id}/movements/{movement_id}/delete", response_class=HTMLResponse)
async def movement_delete(
    request: Request,
    item_id: uuid.UUID,
    movement_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    await get_item_by_id(db, item_id)
    await _check_edit_permission(db, user, item_id)

    movement = await get_movement_by_id(db, movement_id)
    if movement.item_id != item_id:
        raise NotFoundError("Movement not found")
    await delete_movement(db, movement_id)
    await db.commit()

    movements, _ = await get_item_movements(db, item_id)

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("movements/_timeline.html")
    html = template.render(
        movements=movements,
        item_id=item_id,
        show_delete=True,
        current_user=user,
    )
    return HTMLResponse(content=html)


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
    html = template.render(movements=movements, current_user=user)
    return HTMLResponse(content=html)
