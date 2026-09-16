from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import Response

from app.auth.service import (
    COOKIE_SESSION,
    AuthUser,
    verify_session_token,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SessionData:
    user: AuthUser


def _secure_cookie_settings() -> dict[str, str | bool]:
    from app.config import get_settings

    settings = get_settings()
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.is_production,
    }


def get_session(request: Request) -> SessionData | None:
    """Extract and validate session from the nesti_session cookie."""
    token = request.cookies.get(COOKIE_SESSION)
    if not token:
        return None

    user = verify_session_token(token)
    if user is None:
        return None

    return SessionData(user=user)


def set_session(response: Response, token: str) -> None:
    """Set the session cookie on the response."""
    response.set_cookie(
        COOKIE_SESSION,
        token,
        max_age=60 * 60 * 24 * 7,
        path="/",
        httponly=True,
        samesite="lax",
        secure=_is_secure(),
    )


def clear_session(response: Response) -> None:
    """Clear the session cookie."""
    response.delete_cookie(COOKIE_SESSION, path="/")


def _is_secure() -> bool:
    from app.config import get_settings

    return get_settings().is_production
