from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import auth_service
from app.db.engine import get_db
from app.dependencies import get_current_user, require_admin
from app.users.models import User
from app.users.schemas import UserCreate, UserUpdate
from app.users.service import (
    create_user,
    deactivate_user,
    delete_user,
    get_user_by_id,
    list_users,
    reactivate_user,
    update_user,
)

router = APIRouter(prefix="/admin/users", tags=["admin"])
profile_router = APIRouter(tags=["profile"])


@profile_router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """User profile page."""
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("users/profile.html")
    html = template.render(user=user, current_user=user)
    return HTMLResponse(content=html)


@profile_router.post("/profile")
async def profile_update(
    request: Request,
    display_name: str = Form(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Update user profile."""
    await update_user(db, user.id, UserUpdate(display_name=display_name.strip() or None))
    return RedirectResponse(url="/profile", status_code=303)


@router.get("", response_class=HTMLResponse)
async def users_list(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Admin: list all users."""
    users, total = await list_users(db, include_inactive=True)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("users/list.html")
    html = template.render(users=users, total=total, current_user=current_user)
    return HTMLResponse(content=html)


@router.get("/new", response_class=HTMLResponse)
async def user_create_form(
    request: Request,
    current_user: User = Depends(require_admin),
    error: str | None = None,
) -> HTMLResponse:
    """Admin: new user form."""
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("users/form.html")
    html = template.render(user=None, current_user=current_user, error=error)
    return HTMLResponse(content=html)


@router.post("/new")
async def user_create(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(""),
    role: str = Form("viewer"),
    password: str = Form(""),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Admin: create user."""
    if password:
        supabase_id = await auth_service.admin_create_user(email, password)
        if supabase_id is None:
            jinja_env: Environment = request.app.state.jinja_env
            template = jinja_env.get_template("users/form.html")
            html = template.render(
                user=None,
                current_user=current_user,
                error="Failed to create user in Supabase Auth",
            )
            return HTMLResponse(content=html)
    else:
        supabase_id = None
    data = UserCreate(email=email, display_name=display_name.strip() or None, role=role)
    user = await create_user(db, data, supabase_id=supabase_id)
    return RedirectResponse(url=f"/admin/users/{user.id}", status_code=303)


@router.get("/{user_id}", response_class=HTMLResponse)
async def user_detail(
    request: Request,
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Admin: view user details."""
    user = await get_user_by_id(db, user_id)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("users/detail.html")
    html = template.render(user=user, current_user=current_user)
    return HTMLResponse(content=html)


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def user_edit_form(
    request: Request,
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Admin: edit user form."""
    user = await get_user_by_id(db, user_id)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("users/form.html")
    html = template.render(user=user, current_user=current_user)
    return HTMLResponse(content=html)


@router.post("/{user_id}/edit")
async def user_edit(
    user_id: uuid.UUID,
    request: Request,
    email: str = Form(...),
    display_name: str = Form(""),
    role: str = Form("viewer"),
    is_active: bool = Form(True),
    password: str = Form(""),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Admin: update user."""
    data = UserUpdate(display_name=display_name.strip() or None, role=role, is_active=is_active)
    await update_user(db, user_id, data)
    if password:
        user = await get_user_by_id(db, user_id)
        await auth_service.admin_update_password(user.supabase_id, password)
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


@router.post("/{user_id}/role")
async def change_role(
    user_id: uuid.UUID,
    request: Request,
    role: str = Form(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Admin: change user role."""
    await update_user(db, user_id, UserUpdate(role=role))
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


@router.post("/{user_id}/deactivate")
async def deactivate(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Admin: deactivate user."""
    await deactivate_user(db, user_id)
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/{user_id}/reactivate")
async def reactivate(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Admin: reactivate user."""
    await reactivate_user(db, user_id)
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


@router.post("/{user_id}/delete")
async def user_delete(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Admin: hard delete user."""
    user = await get_user_by_id(db, user_id)
    await auth_service.admin_delete_user(user.supabase_id)
    await delete_user(db, user_id)
    return RedirectResponse(url="/admin/users", status_code=303)
