from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.config import get_settings
from app.users.models import User
from app.users.schemas import UserCreate, UserUpdate


async def list_users(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
    include_inactive: bool = False,
) -> tuple[list[User], int]:
    """List all users with pagination."""
    query = select(User)
    count_query = select(func.count()).select_from(User)

    if not include_inactive:
        query = query.where(User.is_active.is_(True))
        count_query = count_query.where(User.is_active.is_(True))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    query = query.order_by(User.email).offset(offset).limit(per_page)

    result = await db.execute(query)
    users = list(result.scalars().all())

    return users, total


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User:
    """Get a user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")
    return user


async def create_user(
    db: AsyncSession,
    data: UserCreate,
) -> User:
    """Create a new user."""
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("User with this email already exists")

    user = User(
        email=data.email,
        display_name=data.display_name,
        role=data.role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Hard delete a user."""
    user = await get_user_by_id(db, user_id)
    await db.delete(user)
    await db.flush()


async def update_user(db: AsyncSession, user_id: uuid.UUID, data: UserUpdate) -> User:
    """Update user fields."""
    user = await get_user_by_id(db, user_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    """Deactivate a user (soft delete)."""
    user = await get_user_by_id(db, user_id)
    user.is_active = False
    await db.flush()
    await db.refresh(user)
    return user


async def reactivate_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    """Reactivate a deactivated user."""
    user = await get_user_by_id(db, user_id)
    user.is_active = True
    await db.flush()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get a user by email (case-insensitive)."""
    result = await db.execute(
        select(User).where(func.lower(User.email) == email.lower())
    )
    return result.scalar_one_or_none()


async def set_password(db: AsyncSession, user: User, password_hash: str) -> None:
    """Persist a password hash for the user."""
    user.password_hash = password_hash
    await db.flush()


async def set_totp_secret(db: AsyncSession, user: User, secret: str) -> None:
    """Enable 2FA for the user by storing their TOTP secret."""
    user.totp_secret = secret
    await db.flush()


async def clear_totp_secret(db: AsyncSession, user: User) -> None:
    """Disable 2FA by clearing the stored TOTP secret."""
    user.totp_secret = None
    await db.flush()


def _utc_now_naive() -> datetime:
    """Return current UTC time as a naive datetime (for SQLite compatibility)."""
    return datetime.now(UTC).replace(tzinfo=None)


async def is_account_locked(
    db: AsyncSession, user: User, *, now: datetime | None = None
) -> bool:
    """Return True when the account is temporarily locked due to failed logins."""
    if user.locked_until is None:
        return False
    now = now or _utc_now_naive()
    locked = (
        user.locked_until.replace(tzinfo=None)
        if user.locked_until.tzinfo
        else user.locked_until
    )
    if locked <= now:
        user.locked_until = None
        await db.flush()
        return False
    return True


async def register_failed_login(db: AsyncSession, user: User) -> None:
    """Increment the failed-login counter, locking the account at the threshold."""
    settings = get_settings()
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= settings.login_max_attempts:
        user.locked_until = _utc_now_naive() + timedelta(
            seconds=settings.login_lockout_seconds
        )
    await db.flush()


async def reset_login_attempts(db: AsyncSession, user: User) -> None:
    """Reset the failed-login counter and lockout after a successful login."""
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.flush()
