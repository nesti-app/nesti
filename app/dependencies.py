from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import SessionData, get_session
from app.db.engine import get_db
from app.users.models import User
from app.users.service import ensure_user_exists


async def get_current_user(
    session: SessionData | None = Depends(get_session),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from the session.

    Auto-creates the user record on first login if it does not yet exist
    (first user in an empty database is bootstrapped as admin).
    """
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Cookie"},
        )

    user = await ensure_user_exists(
        db, session.user.supabase_id, session.user.email
    )

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

    result = await db.execute(select(User).where(User.supabase_id == session.user.supabase_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None

    return user


def require_role(*roles: str):
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
