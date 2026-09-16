from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import SessionData, get_session
from app.common.exceptions import NotFoundError
from app.db.engine import get_db
from app.users.models import User
from app.users.service import get_user_by_id


async def get_current_user(
    session: SessionData | None = Depends(get_session),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from the session cookie.

    The user ID comes from the signed session token; the record is looked up
    in the local database (no auto-creation on first login).
    """
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Cookie"},
        )

    try:
        user = await get_user_by_id(db, uuid.UUID(session.user.user_id))
    except (NotFoundError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Cookie"},
        ) from None

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


async def get_optional_user(
    session: SessionData | None = Depends(get_session),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get the current user if authenticated, otherwise None."""
    if session is None:
        return None

    try:
        user = await get_user_by_id(db, uuid.UUID(session.user.user_id))
    except (NotFoundError, ValueError):
        return None

    if not user.is_active:
        return None

    return user


def require_role(*roles: str) -> Callable[..., Awaitable[User]]:
    """Dependency factory that requires the user to have one of the specified roles."""

    async def _check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(roles)}",
            )
        return user

    return _check_role


require_admin = require_role("admin")
require_editor = require_role("admin", "editor")
