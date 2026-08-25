from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

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
    update_scope,
)
from app.db.engine import get_db
from app.dependencies import require_admin
from app.users.models import User

router = APIRouter(prefix="/access", tags=["access"])


@router.get("", response_class=HTMLResponse)
async def access_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    scopes, total = await list_scopes(db)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("access/list.html")
    html = template.render(scopes=scopes, total=total, current_user=request.state.current_user)
    return HTMLResponse(content=html)


@router.get("/new", response_class=None)
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
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    scope = await get_scope_by_id(db, scope_id)
    matched_count = await count_matching_items(db, scope_id)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("access/detail.html")
    html = template.render(
        scope=scope,
        matched_count=matched_count,
        current_user=request.state.current_user,
    )
    return HTMLResponse(content=html)


@router.get("/{scope_id}/edit", response_class=None)
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
