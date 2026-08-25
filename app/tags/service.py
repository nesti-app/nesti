from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.tags.models import Tag
from app.tags.schemas import TagCreate, TagUpdate


async def list_tags(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 100,
) -> tuple[list[Tag], int]:
    """List all tags with pagination."""
    count_result = await db.execute(select(func.count()).select_from(Tag))
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(select(Tag).order_by(Tag.name).offset(offset).limit(per_page))
    return list(result.scalars().all()), total


async def get_tag_by_id(db: AsyncSession, tag_id: uuid.UUID) -> Tag:
    """Get a tag by ID."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if tag is None:
        raise NotFoundError("Tag not found")
    return tag


async def get_tag_by_name(db: AsyncSession, name: str) -> Tag | None:
    """Get a tag by name."""
    result = await db.execute(select(Tag).where(Tag.name == name))
    return result.scalar_one_or_none()


async def create_tag(db: AsyncSession, data: TagCreate) -> Tag:
    """Create a new tag."""
    existing = await get_tag_by_name(db, data.name)
    if existing is not None:
        raise ConflictError("Tag with this name already exists")

    tag = Tag(name=data.name)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return tag


async def update_tag(db: AsyncSession, tag_id: uuid.UUID, data: TagUpdate) -> Tag:
    """Update a tag."""
    tag = await get_tag_by_id(db, tag_id)

    if data.name != tag.name:
        existing = await get_tag_by_name(db, data.name)
        if existing is not None:
            raise ConflictError("Tag with this name already exists")

    tag.name = data.name
    await db.flush()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag_id: uuid.UUID) -> None:
    """Delete a tag."""
    tag = await get_tag_by_id(db, tag_id)
    await db.delete(tag)
    await db.flush()


async def search_tags(db: AsyncSession, query: str, limit: int = 20) -> list[Tag]:
    """Search tags by name prefix."""
    result = await db.execute(
        select(Tag).where(Tag.name.ilike(f"%{query}%")).order_by(Tag.name).limit(limit)
    )
    return list(result.scalars().all())
