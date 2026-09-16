from __future__ import annotations

import io
import uuid

import qrcode
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import (
    generate_totp_secret,
    hash_password,
    totp_uri,
    verify_totp,
)
from app.db.engine import get_db
from app.dependencies import get_current_user, require_admin
from app.users.models import User
from app.users.schemas import UserCreate, UserUpdate
from app.users.service import (
    clear_totp_secret,
    create_user,
    deactivate_user,
    delete_user,
    get_user_by_id,
    list_users,
    reactivate_user,
    reset_login_attempts,
    set_password,
    set_totp_secret,
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
    """Admin: create user. Password is hashed locally when provided."""
    data = UserCreate(email=email, display_name=display_name.strip() or None, role=role)
    user = await create_user(db, data)
    if password:
        await set_password(db, user, hash_password(password))
        await db.commit()
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
    """Admin: update user. Set password when non-empty."""
    data = UserUpdate(display_name=display_name.strip() or None, role=role, is_active=is_active)
    await update_user(db, user_id, data)
    if password:
        user = await get_user_by_id(db, user_id)
        await set_password(db, user, hash_password(password))
        await db.commit()
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


@router.post("/{user_id}/unlock")
async def unlock_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Admin: unlock a locked-out user."""
    user = await get_user_by_id(db, user_id)
    await reset_login_attempts(db, user)
    await db.commit()
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


@router.post("/{user_id}/disable-2fa")
async def disable_2fa(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Admin: disable 2FA for a user."""
    user = await get_user_by_id(db, user_id)
    await clear_totp_secret(db, user)
    await db.commit()
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: uuid.UUID,
    request: Request,
    new_password: str = Form(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Admin: reset a user's password."""
    user = await get_user_by_id(db, user_id)
    await set_password(db, user, hash_password(new_password))
    await db.commit()
    return RedirectResponse(url=f"/admin/users/{user_id}", status_code=303)


@router.post("/{user_id}/delete")
async def user_delete(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Admin: hard delete user (local DB only)."""
    await delete_user(db, user_id)
    return RedirectResponse(url="/admin/users", status_code=303)


# --- 2FA self-service ---


def _totp_qr_svg(uri: str) -> str:
    """Render the otpauth:// URI as a data-URI-free inline SVG."""
    from qrcode.image.svg import SvgPathImage

    buf = io.BytesIO()
    qrcode.make(uri, image_factory=SvgPathImage, box_size=8, border=2).save(buf)
    svg = buf.getvalue().decode("utf-8")
    # Trim XML declaration + drop width/height so it scales with CSS
    svg = svg.split(">", 1)[1] if svg.startswith("<") else svg
    return svg


@profile_router.get("/profile/2fa", response_class=HTMLResponse)
async def enable_2fa_form(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Show 2FA setup page: generate secret + QR."""
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("users/2fa.html")
    if user.totp_secret:
        # Already enabled — show status page
        html = template.render(user=user, enabled=True)
        return HTMLResponse(content=html)

    secret = generate_totp_secret()
    uri = totp_uri(user.email, secret)
    qr_svg = _totp_qr_svg(uri)
    html = template.render(
        user=user,
        enabled=False,
        secret=secret,
        totp_uri=uri,
        qr_svg=qr_svg,
    )
    return HTMLResponse(content=html)


@profile_router.post("/profile/2fa/confirm")
async def confirm_2fa(
    request: Request,
    code: str = Form(...),
    secret: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Verify the code and persist the TOTP secret (enable 2FA)."""
    if verify_totp(secret, code.strip()):
        await set_totp_secret(db, user, secret)
        await db.commit()
        return RedirectResponse(url="/profile", status_code=303)
    # Bad code: re-render form with error
    uri = totp_uri(user.email, secret)
    qr_svg = _totp_qr_svg(uri)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("users/2fa.html")
    html = template.render(
        user=user,
        enabled=False,
        secret=secret,
        totp_uri=uri,
        qr_svg=qr_svg,
        error="Invalid code. Try again.",
    )
    return HTMLResponse(content=html)


@profile_router.post("/profile/2fa/disable")
async def disable_2fa_self(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Disable 2FA for the current user."""
    await clear_totp_secret(db, user)
    await db.commit()
    return RedirectResponse(url="/profile", status_code=303)
