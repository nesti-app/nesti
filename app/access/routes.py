from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.access.schemas import (
    AccessScopeCreate,
    AccessScopePermissionCreate,
    AccessScopeRuleCreate,
    AccessScopeUpdate,
    AccessScopeUserCreate,
)
from app.access.service import (
    add_permission,
    add_rule,
    assign_user,
    count_matching_items,
    create_scope,
    delete_scope,
    get_scope_by_id,
    list_scopes,
    remove_permission,
    remove_rule,
    remove_user,
    resolve_rule_display,
    update_scope,
)
from app.db.engine import get_db
from app.dependencies import get_current_user, require_admin
from app.users.models import User

router = APIRouter(prefix="/access", tags=["access"])


@router.get("", response_class=HTMLResponse)
async def access_list(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    scopes, total = await list_scopes(db)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("access/list.html")
    html = template.render(scopes=scopes, total=total, current_user=user)
    return HTMLResponse(content=html)


@router.get("/search/locations/json")
async def locations_search(q: str = "", db: AsyncSession = Depends(get_db)) -> list[dict]:
    from app.locations.models import Location

    query = select(Location).options(selectinload(Location.parent)).order_by(Location.name)
    if q:
        query = query.where(Location.name.ilike(f"%{q}%"))
    query = query.limit(20)
    result = await db.execute(query)
    locations = list(result.scalars().all())
    return [
        {
            "id": str(loc.id),
            "name": loc.name,
            "display": f"{loc.parent.name} → {loc.name}" if loc.parent else loc.name,
        }
        for loc in locations
    ]


@router.get("/search/categories/json")
async def categories_search(q: str = "", db: AsyncSession = Depends(get_db)) -> list[dict]:
    from app.categories.models import Category

    query = select(Category).options(selectinload(Category.parent)).order_by(Category.name)
    if q:
        query = query.where(Category.name.ilike(f"%{q}%"))
    query = query.limit(20)
    result = await db.execute(query)
    categories = list(result.scalars().all())
    return [
        {
            "id": str(cat.id),
            "name": cat.name,
            "display": f"{cat.parent.name} → {cat.name}" if cat.parent else cat.name,
        }
        for cat in categories
    ]


@router.get("/search/tags/json")
async def tags_search(q: str = "", db: AsyncSession = Depends(get_db)) -> list[dict]:
    from app.tags.models import Tag

    query = select(Tag).order_by(Tag.name)
    if q:
        query = query.where(Tag.name.ilike(f"%{q}%"))
    query = query.limit(20)
    result = await db.execute(query)
    tags = list(result.scalars().all())
    return [{"id": str(t.id), "name": t.name, "display": t.name} for t in tags]


@router.get("/search/items/json")
async def items_search(q: str = "", db: AsyncSession = Depends(get_db)) -> list[dict]:
    from app.items.models import Item

    query = select(Item).order_by(Item.name)
    if q:
        query = query.where(Item.name.ilike(f"%{q}%"))
    query = query.limit(20)
    result = await db.execute(query)
    items = list(result.scalars().all())
    return [
        {
            "id": str(item.id),
            "name": item.name,
            "display": f"{item.name} ({item.short_code})",
        }
        for item in items
    ]


@router.get("/users/json")
async def users_search(q: str = "", db: AsyncSession = Depends(get_db)) -> list[dict]:
    query = select(User).order_by(User.email)
    if q:
        query = query.where(
            User.email.ilike(f"%{q}%") | User.display_name.ilike(f"%{q}%")
        )
    query = query.limit(20)
    result = await db.execute(query)
    users = list(result.scalars().all())
    return [
        {
            "id": str(u.id),
            "display": f"{u.display_name} ({u.email})" if u.display_name else u.email,
        }
        for u in users
    ]


@router.get("/new", response_class=HTMLResponse)
async def access_create_form(
    request: Request,
    user: User = Depends(require_admin),
) -> Response:
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("access/form.html")
    html = template.render(scope=None, current_user=user)
    return HTMLResponse(content=html)


@router.post("/new")
async def access_create_submit(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = AccessScopeCreate(name=name, description=description or None)
    scope = await create_scope(db, data)
    return RedirectResponse(url=f"/access/{scope.id}", status_code=303)


@router.get("/{scope_id}", response_class=HTMLResponse)
async def access_detail(
    request: Request,
    scope_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    scope = await get_scope_by_id(db, scope_id)
    matched_count = await count_matching_items(db, scope_id)
    rule_displays = {}
    for rule in scope.rules:
        rule_displays[rule.id] = await resolve_rule_display(db, rule.rule_type, rule.rule_value)
    user_displays = {}
    for su in scope.users:
        if su.user:
            user_displays[su.user_id] = (
                f"{su.user.display_name} ({su.user.email})"
                if su.user.display_name
                else su.user.email
            )
        else:
            user_displays[su.user_id] = str(su.user_id)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("access/detail.html")
    html = template.render(
        scope=scope,
        matched_count=matched_count,
        rule_displays=rule_displays,
        user_displays=user_displays,
        current_user=user,
    )
    return HTMLResponse(content=html)


@router.get("/{scope_id}/edit", response_class=HTMLResponse)
async def access_edit_form(
    request: Request,
    scope_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    scope = await get_scope_by_id(db, scope_id)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("access/form.html")
    html = template.render(scope=scope, current_user=user)
    return HTMLResponse(content=html)


@router.post("/{scope_id}/edit")
async def access_edit_submit(
    scope_id: uuid.UUID,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = AccessScopeUpdate(name=name, description=description or None)
    await update_scope(db, scope_id, data)
    return RedirectResponse(url=f"/access/{scope_id}", status_code=303)


@router.post("/{scope_id}/delete")
async def access_delete(
    scope_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await delete_scope(db, scope_id)
    return RedirectResponse(url="/access", status_code=303)


@router.post("/{scope_id}/rules")
async def access_add_rule(
    scope_id: uuid.UUID,
    request: Request,
    rule_type: str = Form(...),
    rule_value: str = Form(...),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = AccessScopeRuleCreate(rule_type=rule_type, rule_value=rule_value)
    await add_rule(db, scope_id, data)
    return RedirectResponse(url=f"/access/{scope_id}", status_code=303)


@router.post("/{scope_id}/rules/{rule_id}/delete")
async def access_remove_rule(
    scope_id: uuid.UUID,
    rule_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await remove_rule(db, scope_id, rule_id)
    return RedirectResponse(url=f"/access/{scope_id}", status_code=303)


@router.post("/{scope_id}/permissions")
async def access_add_permission(
    scope_id: uuid.UUID,
    request: Request,
    permission: str = Form(...),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = AccessScopePermissionCreate(permission=permission)
    await add_permission(db, scope_id, data)
    return RedirectResponse(url=f"/access/{scope_id}", status_code=303)


@router.post("/{scope_id}/permissions/{permission_id}/delete")
async def access_remove_permission(
    scope_id: uuid.UUID,
    permission_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await remove_permission(db, scope_id, permission_id)
    return RedirectResponse(url=f"/access/{scope_id}", status_code=303)


@router.post("/{scope_id}/users")
async def access_assign_user(
    scope_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Form(...),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = AccessScopeUserCreate(user_id=user_id)
    await assign_user(db, scope_id, data)
    return RedirectResponse(url=f"/access/{scope_id}", status_code=303)


@router.post("/{scope_id}/users/{user_id}/delete")
async def access_remove_user(
    scope_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await remove_user(db, scope_id, user_id)
    return RedirectResponse(url=f"/access/{scope_id}", status_code=303)
