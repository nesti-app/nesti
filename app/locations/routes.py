from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.dependencies import get_current_user, require_admin
from app.locations.schemas import LocationCreate, LocationUpdate
from app.locations.service import (
    build_tree,
    create_location,
    delete_location,
    get_location_by_id,
    list_locations,
    update_location,
)
from app.users.models import User

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_class=HTMLResponse)
async def locations_list(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    locations, total = await list_locations(db)
    tree = await build_tree(locations)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("locations/list.html")
    html = template.render(
        locations=locations,
        tree=tree,
        total=total,
        current_user=user,
    )
    return HTMLResponse(content=html)


@router.get("/new", response_class=HTMLResponse)
async def location_create_form(
    request: Request,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    locations, _ = await list_locations(db)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("locations/form.html")
    html = template.render(location=None, locations=locations, current_user=user)
    return HTMLResponse(content=html)


@router.post("/new")
async def location_create_submit(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    parent_location_id: uuid.UUID | None = Form(None),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = LocationCreate(
        name=name,
        description=description or None,
        parent_location_id=parent_location_id,
    )
    await create_location(db, data)
    return RedirectResponse(url="/locations", status_code=303)


@router.get("/{location_id}", response_class=HTMLResponse)
async def location_detail(
    request: Request,
    location_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    location = await get_location_by_id(db, location_id)

    from app.items.models import Item
    from app.items.service import list_items

    items, total = await list_items(db, filters=[Item.location_id == location_id])

    can_edit = user.role in ("admin", "editor")

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("locations/detail.html")
    html = template.render(
        location=location, items=items, total=total,
        can_edit=can_edit, current_user=user,
    )
    return HTMLResponse(content=html)


@router.get("/{location_id}/edit", response_class=HTMLResponse)
async def location_edit_form(
    request: Request,
    location_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    location = await get_location_by_id(db, location_id)
    locations, _ = await list_locations(db)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("locations/form.html")
    html = template.render(location=location, locations=locations, current_user=user)
    return HTMLResponse(content=html)


@router.post("/{location_id}/edit")
async def location_edit_submit(
    location_id: uuid.UUID,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    parent_location_id: uuid.UUID | None = Form(None),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = LocationUpdate(
        name=name,
        description=description or None,
        parent_location_id=parent_location_id,
    )
    await update_location(db, location_id, data)
    return RedirectResponse(url=f"/locations/{location_id}", status_code=303)


@router.post("/{location_id}/delete")
async def location_delete(
    location_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await delete_location(db, location_id)
    return RedirectResponse(url="/locations", status_code=303)
