from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.dependencies import require_admin
from app.users.models import User
from app.users.schemas import UserUpdate
from app.users.service import (
    deactivate_user,
    get_user_by_id,
    list_users,
    reactivate_user,
    update_user,
)

router = APIRouter(prefix="/admin/users", tags=["admin"])


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


@router.post("/{user_id}/role")
async def change_role(
    user_id: uuid.UUID,
    role: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Admin: change user role."""
    from fastapi.responses import RedirectResponse

    await update_user(db, user_id, UserUpdate(role=role))
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


@router.post("/{user_id}/deactivate")
async def deactivate(
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Admin: deactivate user."""
    from fastapi.responses import RedirectResponse

    await deactivate_user(db, user_id)
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/{user_id}/reactivate")
async def reactivate(
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Admin: reactivate user."""
    from fastapi.responses import RedirectResponse

    await reactivate_user(db, user_id)
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)
