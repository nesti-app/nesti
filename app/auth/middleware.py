from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import RedirectResponse

from app.auth.service import AuthUser, auth_service
from app.config import get_settings

SESSION_COOKIE_NAME = "nesti_session"

_cookie_settings = {
    "httponly": True,
    "samesite": "lax",
}


def _secure_cookie_settings() -> dict[str, bool]:
    settings = get_settings()
    return {
        **_cookie_settings,
        "secure": settings.is_production,
    }


@dataclass(frozen=True)
class SessionData:
    access_token: str
    refresh_token: str
    user: AuthUser


def get_session(request: Request) -> SessionData | None:
    """Extract and validate session from request cookies."""
    access_token = request.cookies.get(f"{SESSION_COOKIE_NAME}_access")
    refresh_token = request.cookies.get(f"{SESSION_COOKIE_NAME}_refresh")

    if not access_token or not refresh_token:
        return None

    user = auth_service.verify_token(access_token)
    if user is None:
        return None

    return SessionData(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user,
    )


def set_session(
    response: RedirectResponse,
    access_token: str,
    refresh_token: str,
) -> None:
    """Set session cookies on the response."""
    secure = _secure_cookie_settings()
    max_age_access = 60 * 60  # 1 hour
    max_age_refresh = 60 * 60 * 24 * 7  # 7 days

    response.set_cookie(
        f"{SESSION_COOKIE_NAME}_access",
        access_token,
        max_age=max_age_access,
        path="/",
        **secure,
    )
    response.set_cookie(
        f"{SESSION_COOKIE_NAME}_refresh",
        refresh_token,
        max_age=max_age_refresh,
        path="/",
        **secure,
    )


def clear_session(response: RedirectResponse) -> None:
    """Clear session cookies."""
    response.delete_cookie(f"{SESSION_COOKIE_NAME}_access", path="/")
    response.delete_cookie(f"{SESSION_COOKIE_NAME}_refresh", path="/")
