from __future__ import annotations

import time
import uuid
from collections import defaultdict

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import clear_session, get_session, set_session
from app.auth.service import (
    COOKIE_PENDING_2FA,
    create_pending_2fa_token,
    create_session_token,
    verify_password,
    verify_pending_2fa_token,
    verify_totp,
)
from app.db.engine import _get_session_factory
from app.users.models import User
from app.users.service import (
    get_user_by_email,
    is_account_locked,
    register_failed_login,
    reset_login_attempts,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# In-process sliding window: ip -> [timestamps]. Documented as per-instance only.
_ip_attempts: dict[str, list[float]] = defaultdict(list)


def _is_ip_throttled(request: Request) -> bool:
    from app.config import get_settings

    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = [_ for _ in _ip_attempts[client_ip] if now - _ < 60]
    if len(window) >= settings.ip_throttle_per_minute:
        _ip_attempts[client_ip] = window
        return True
    window.append(now)
    _ip_attempts[client_ip] = window
    return False


def _login_error(request: Request, error: str) -> Response:
    return RedirectResponse(url=f"/auth/login?error={error}", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    """Show login page (step 1) or redirect when already authenticated."""
    session = get_session(request)
    if session is not None:
        return RedirectResponse(url="/", status_code=303)

    error = request.query_params.get("error")
    pending_token = request.cookies.get(COOKIE_PENDING_2FA)
    jinja_env: Environment = request.app.state.jinja_env

    if pending_token:
        user_id = verify_pending_2fa_token(pending_token)
        if user_id:
            template = jinja_env.get_template("auth/login.html")
            html = template.render(error=error, pending_2fa=True, pending_user_id=user_id)
            return HTMLResponse(content=html)

    template = jinja_env.get_template("auth/login.html")
    html = template.render(error=error, pending_2fa=False, pending_user_id=None)
    return HTMLResponse(content=html)


async def _authenticate_user(
    db: AsyncSession,
    user: User,
    password: str,
) -> bool:
    """Check a password; handle anti-bruteforce counting. Returns success."""
    if await is_account_locked(db, user):
        return False
    if not user.password_hash or not verify_password(
        password, user.password_hash
    ):
        await register_failed_login(db, user)
        await db.commit()
        return False
    await reset_login_attempts(db, user)
    await db.commit()
    return True


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
) -> Response:
    """Authenticate user locally with email/password (step 1)."""
    if _is_ip_throttled(request):
        return _login_error(request, "too_many_requests")

    async with _get_session_factory()() as db:
        user = await get_user_by_email(db, email)
        if user is None:
            # No account: run a dummy verify to keep timing roughly constant
            # and avoid leaking which emails exist.
            verify_password(password, "$argon2id$v=19$m=65536,t=3,p=4$AAAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")  # noqa: E501
            return _login_error(request, "invalid_credentials")

        if not user.is_active:
            return _login_error(request, "invalid_credentials")

        ok = await _authenticate_user(db, user, password)
        if not ok:
            locked = await is_account_locked(db, user)
            error = "account_locked" if locked else "invalid_credentials"
            return _login_error(request, error)

        if user.totp_secret:
            pending = create_pending_2fa_token(str(user.id))
            response = RedirectResponse(url="/auth/login", status_code=303)
            response.set_cookie(
                COOKIE_PENDING_2FA,
                pending,
                max_age=5 * 60,
                path="/",
                httponly=True,
                samesite="lax",
                secure=request.url.scheme == "https",
            )
            return response

        token = create_session_token(str(user.id), user.email)
        response = RedirectResponse(url="/", status_code=303)
        set_session(response, token)
        return response


@router.post("/login/2fa")
async def login_2fa_submit(
    request: Request,
    code: str = Form(...),
) -> Response:
    """Step 2: verify the TOTP code for a user in the pending_2fa state."""
    if _is_ip_throttled(request):
        return _login_error(request, "too_many_requests")

    pending_token = request.cookies.get(COOKIE_PENDING_2FA)
    if not pending_token:
        return _login_error(request, "invalid_credentials")
    user_id_raw = verify_pending_2fa_token(pending_token)
    if user_id_raw is None:
        return _login_error(request, "invalid_credentials")
    try:
        user_id = uuid.UUID(user_id_raw)
    except ValueError:
        return _login_error(request, "invalid_credentials")

    async with _get_session_factory()() as db:
        user = await db.get(User, user_id)
        if user is None or not user.is_active or not user.totp_secret:
            return _login_error(request, "invalid_credentials")

        if await is_account_locked(db, user):
            return _login_error(request, "account_locked")

        if not verify_totp(user.totp_secret, code.strip()):
            await register_failed_login(db, user)
            await db.commit()
            error = "account_locked" if await is_account_locked(db, user) else "invalid_code"
            return _login_error(request, error)

        await reset_login_attempts(db, user)
        await db.commit()

        token = create_session_token(str(user.id), user.email)
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie(COOKIE_PENDING_2FA, path="/")
        set_session(response, token)
        return response


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Log out the current user."""
    response = RedirectResponse(url="/auth/login", status_code=303)
    clear_session(response)
    response.delete_cookie(COOKIE_PENDING_2FA, path="/")
    return response
