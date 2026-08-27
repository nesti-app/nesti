from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
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


async def get_user_by_supabase_id(db: AsyncSession, supabase_id: str) -> User | None:
    """Get a user by Supabase ID."""
    result = await db.execute(select(User).where(User.supabase_id == supabase_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    data: UserCreate,
    supabase_id: str | None = None,
) -> User:
    """Create a new user. supabase_id comes from Supabase Auth after invite/signup."""
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("User with this email already exists")

    user = User(
        supabase_id=supabase_id or str(uuid.uuid4()),
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


async def ensure_user_exists(
    db: AsyncSession,
    supabase_id: str,
    email: str,
) -> User:
    """Ensure a user record exists for a Supabase Auth user. Creates if missing.

    The very first user in an empty database is bootstrapped as an admin
    (first-login bootstrap). Subsequent auto-created users default to viewer.
    """
    user = await get_user_by_supabase_id(db, supabase_id)
    if user is not None:
        return user

    result = await db.execute(select(func.count()).select_from(User))
    total = result.scalar_one()

    user = User(
        supabase_id=supabase_id,
        email=email,
        role="admin" if total == 0 else "viewer",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
