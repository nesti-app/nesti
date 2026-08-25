from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenError
from app.db.engine import get_db
from app.dependencies import get_current_user
from app.items.models import Item
from app.items.service import get_item_by_id
from app.relationships.schemas import RelationshipCreate
from app.relationships.service import (
    create_relationship,
    delete_relationship,
    get_item_relationships,
)
from app.users.models import User

router = APIRouter(tags=["relationships"])


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
        raise ForbiddenError("You do not have permission to edit this item's relationships")


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
        raise ForbiddenError("You do not have permission to view this item's relationships")


@router.get("/items/{item_id}/relationships", response_class=HTMLResponse)
async def relationship_list(
    request: Request,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    await get_item_by_id(db, item_id)
    await _check_view_permission(db, user, item_id)
    relationships = await get_item_relationships(db, item_id)

    items_result = await db.execute(select(Item).order_by(Item.name))
    all_items = list(items_result.scalars().all())

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("items/_relationships.html")
    html = template.render(
        item_id=item_id,
        relationships=relationships,
        all_items=all_items,
    )
    return HTMLResponse(content=html)


@router.post("/items/{item_id}/relationships")
async def relationship_add(
    request: Request,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await get_item_by_id(db, item_id)
    await _check_edit_permission(db, user, item_id)

    form = await request.form()
    target_item_id = uuid.UUID(str(form["target_item_id"]))
    relationship_type = str(form["relationship_type"])

    data = RelationshipCreate(
        target_item_id=target_item_id,
        relationship_type=relationship_type,
    )
    await create_relationship(db, item_id, data.target_item_id, data.relationship_type, user.id)
    await db.commit()

    return RedirectResponse(url=f"/items/{item_id}", status_code=303)


@router.post("/items/{item_id}/relationships/{relationship_id}/delete")
async def relationship_remove(
    item_id: uuid.UUID,
    relationship_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await get_item_by_id(db, item_id)
    await _check_edit_permission(db, user, item_id)

    await delete_relationship(db, relationship_id)
    await db.commit()

    return RedirectResponse(url=f"/items/{item_id}", status_code=303)
