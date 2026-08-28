from __future__ import annotations

import contextlib
import uuid
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.access.service import evaluate_user_scopes, get_user_item_permissions
from app.common.exceptions import ForbiddenError
from app.db.engine import get_db
from app.dependencies import get_current_user
from app.items.schemas import ItemCreate, ItemUpdate
from app.items.service import (
    create_item,
    delete_item,
    get_item_by_id,
    list_items,
    update_item,
)
from app.users.models import User

router = APIRouter(prefix="/items", tags=["items"])


async def _check_item_permission(
    db: AsyncSession,
    user: User,
    item_id: uuid.UUID,
    permission: str,
) -> None:
    if user.role == "admin":
        return
    from app.access.service import user_has_item_permission

    has = await user_has_item_permission(db, user.id, item_id, permission)
    if not has:
        raise ForbiddenError("You do not have permission to perform this action")


async def _get_user_item_filters(
    db: AsyncSession,
    user: User,
) -> list | None:
    """Get item filters based on user's access scopes. None means no filter (admin)."""
    if user.role == "admin":
        return None

    scopes = await evaluate_user_scopes(db, user.id)
    if not scopes:
        from app.access.service import _build_item_filters

        return []

    from app.access.service import _build_item_filters

    all_conditions = []
    for scope in scopes:
        scope_perms = {p.permission for p in scope.permissions}
        if "view" not in scope_perms:
            continue
        conditions = await _build_item_filters(db, scope.rules)
        if conditions:
            all_conditions.extend(conditions)

    if not all_conditions:
        return []

    return all_conditions


@router.get("", response_class=HTMLResponse)
async def items_list(
    request: Request,
    page: int = 1,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    filters = await _get_user_item_filters(db, user)
    items, total = await list_items(db, page=page, per_page=50, filters=filters)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("items/list.html")
    html = template.render(items=items, total=total, page=page, current_user=user)
    return HTMLResponse(content=html)


@router.get("/manufacturers/json")
async def manufacturers_search(
    q: str = "",
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    from sqlalchemy import distinct, select

    from app.items.models import Item

    query = (
        select(distinct(Item.manufacturer))
        .where(Item.manufacturer.isnot(None))
        .where(Item.manufacturer != "")
        .order_by(Item.manufacturer)
    )
    if q:
        query = query.where(Item.manufacturer.ilike(f"%{q}%"))
    query = query.limit(20)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


@router.get("/new", response_class=HTMLResponse)
async def item_create_form(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if user.role not in ("admin", "editor"):
        raise ForbiddenError("You do not have permission to create items")

    from app.categories.service import list_categories
    from app.locations.service import list_locations
    from app.tags.service import list_tags

    categories, _ = await list_categories(db)
    locations, _ = await list_locations(db)
    tags, _ = await list_tags(db)

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("items/form.html")
    html = template.render(
        item=None,
        item_tags_json=[],
        categories=categories,
        locations=locations,
        tags=tags,
        current_user=user,
    )
    return HTMLResponse(content=html)


@router.post("/new")
async def item_create_submit(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    category_id: uuid.UUID | None = Form(None),
    location_id: uuid.UUID | None = Form(None),
    parent_item_id: uuid.UUID | None = Form(None),
    manufacturer: str = Form(""),
    model_name: str = Form(""),
    serial_number: str = Form(""),
    sku: str = Form(""),
    purchase_date: str = Form(""),
    purchase_price: str = Form(""),
    currency: str = Form(""),
    notes: str = Form(""),
    tag_names: str = Form(""),
    photo: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if user.role not in ("admin", "editor"):
        raise ForbiddenError("You do not have permission to create items")

    parsed_date = None
    if purchase_date:
        from datetime import date as dt_date

        with contextlib.suppress(ValueError):
            parsed_date = dt_date.fromisoformat(purchase_date)

    parsed_price = None
    if purchase_price:
        with contextlib.suppress(InvalidOperation, ValueError):
            parsed_price = Decimal(purchase_price)

    tag_ids = []
    if tag_names.strip():
        from app.tags.service import get_or_create_tag_by_name

        for raw in tag_names.split(","):
            name_clean = raw.strip()
            if name_clean:
                tag = await get_or_create_tag_by_name(db, name_clean)
                tag_ids.append(tag.id)

    data = ItemCreate(
        name=name,
        description=description or None,
        category_id=category_id,
        location_id=location_id,
        parent_item_id=parent_item_id,
        manufacturer=manufacturer or None,
        model=model_name or None,
        serial_number=serial_number or None,
        sku=sku or None,
        purchase_date=parsed_date,
        purchase_price=parsed_price,
        currency=currency or None,
        notes=notes or None,
        tag_ids=tag_ids,
    )
    item = await create_item(db, data, user_id=user.id)
    await db.commit()

    photo_error = False
    if photo and photo.filename:
        content = await photo.read()
        if content:
            try:
                from app.media.service import upload_image

                await upload_image(
                    db,
                    item_id=item.id,
                    filename=photo.filename,
                    content_type=photo.content_type or "application/octet-stream",
                    data=content,
                    user_id=user.id,
                )
                await db.commit()
            except Exception:
                await db.rollback()
                photo_error = True

    url = f"/items/{item.id}"
    if photo_error:
        url += "?photo_error=1"
    return RedirectResponse(url=url, status_code=303)


@router.get("/{item_id}", response_class=HTMLResponse)
async def item_detail(
    request: Request,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    item = await get_item_by_id(db, item_id)
    await _check_item_permission(db, user, item_id, "view")

    permissions = await get_user_item_permissions(db, user.id, item_id)
    if user.role in ("admin", "editor"):
        permissions.update({"view", "create", "edit", "move", "delete", "manage_images"})

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("items/detail.html")
    gallery_json = [
        f"/items/{item.id}/images/{img.id}/file" for img in item.images
    ]
    html = template.render(
        item=item,
        permissions=permissions,
        current_user=user,
        request=request,
        photo_error=request.query_params.get("photo_error") == "1",
        gallery_json=gallery_json,
    )
    return HTMLResponse(content=html)


@router.get("/{item_id}/edit", response_class=HTMLResponse)
async def item_edit_form(
    request: Request,
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    item = await get_item_by_id(db, item_id)
    await _check_item_permission(db, user, item_id, "edit")

    from app.categories.service import list_categories
    from app.locations.service import list_locations
    from app.tags.service import list_tags

    categories, _ = await list_categories(db)
    locations, _ = await list_locations(db)
    tags, _ = await list_tags(db)

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("items/form.html")
    html = template.render(
        item=item,
        item_tags_json=[{"name": t.name} for t in item.tags],
        categories=categories,
        locations=locations,
        tags=tags,
        current_user=user,
    )
    return HTMLResponse(content=html)


@router.post("/{item_id}/edit")
async def item_edit_submit(
    item_id: uuid.UUID,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    category_id: uuid.UUID | None = Form(None),
    location_id: uuid.UUID | None = Form(None),
    parent_item_id: uuid.UUID | None = Form(None),
    manufacturer: str = Form(""),
    model_name: str = Form(""),
    serial_number: str = Form(""),
    sku: str = Form(""),
    purchase_date: str = Form(""),
    purchase_price: str = Form(""),
    currency: str = Form(""),
    notes: str = Form(""),
    tag_names: str = Form(""),
    photo: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await get_item_by_id(db, item_id)
    await _check_item_permission(db, user, item_id, "edit")

    parsed_date = None
    if purchase_date:
        from datetime import date as dt_date

        with contextlib.suppress(ValueError):
            parsed_date = dt_date.fromisoformat(purchase_date)

    parsed_price = None
    if purchase_price:
        with contextlib.suppress(InvalidOperation, ValueError):
            parsed_price = Decimal(purchase_price)

    tag_ids = None
    if tag_names.strip():
        from app.tags.service import get_or_create_tag_by_name

        tag_ids = []
        for raw in tag_names.split(","):
            name_clean = raw.strip()
            if name_clean:
                tag = await get_or_create_tag_by_name(db, name_clean)
                tag_ids.append(tag.id)
    else:
        tag_ids = []

    data = ItemUpdate(
        name=name,
        description=description or None,
        category_id=category_id,
        location_id=location_id,
        parent_item_id=parent_item_id,
        manufacturer=manufacturer or None,
        model=model_name or None,
        serial_number=serial_number or None,
        sku=sku or None,
        purchase_date=parsed_date,
        purchase_price=parsed_price,
        currency=currency or None,
        notes=notes or None,
        tag_ids=tag_ids,
    )
    await update_item(db, item_id, data, user_id=user.id)
    await db.commit()

    photo_error = False
    if photo and photo.filename:
        content = await photo.read()
        if content:
            try:
                from app.media.service import upload_image

                await upload_image(
                    db,
                    item_id=item_id,
                    filename=photo.filename,
                    content_type=photo.content_type or "application/octet-stream",
                    data=content,
                    user_id=user.id,
                )
                await db.commit()
            except Exception:
                await db.rollback()
                photo_error = True

    url = f"/items/{item_id}"
    if photo_error:
        url += "?photo_error=1"
    return RedirectResponse(url=url, status_code=303)


@router.post("/{item_id}/delete")
async def item_delete(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await get_item_by_id(db, item_id)
    await _check_item_permission(db, user, item_id, "delete")
    await delete_item(db, item_id)
    return RedirectResponse(url="/items", status_code=303)
