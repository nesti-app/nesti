from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.items.models import Item, ItemRelationship


async def create_relationship(
    db: AsyncSession,
    source_item_id: uuid.UUID,
    target_item_id: uuid.UUID,
    relationship_type: str,
    user_id: uuid.UUID,
) -> ItemRelationship:
    source = await db.get(Item, source_item_id)
    if source is None:
        raise NotFoundError("Source item not found")

    target = await db.get(Item, target_item_id)
    if target is None:
        raise NotFoundError("Target item not found")

    if source_item_id == target_item_id:
        raise ConflictError("Cannot create relationship to self")

    existing = await db.execute(
        select(ItemRelationship).where(
            and_(
                ItemRelationship.source_item_id == source_item_id,
                ItemRelationship.target_item_id == target_item_id,
                ItemRelationship.relationship_type == relationship_type,
            )
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("This relationship already exists")

    rel = ItemRelationship(
        source_item_id=source_item_id,
        target_item_id=target_item_id,
        relationship_type=relationship_type,
        created_by=user_id,
    )
    db.add(rel)
    await db.flush()
    await db.refresh(rel)
    return rel


async def delete_relationship(
    db: AsyncSession,
    relationship_id: uuid.UUID,
) -> None:
    rel = await db.get(ItemRelationship, relationship_id)
    if rel is None:
        raise NotFoundError("Relationship not found")
    await db.delete(rel)
    await db.flush()


async def get_item_relationships(
    db: AsyncSession,
    item_id: uuid.UUID,
) -> list[ItemRelationship]:
    result = await db.execute(
        select(ItemRelationship).where(
            or_(
                ItemRelationship.source_item_id == item_id,
                ItemRelationship.target_item_id == item_id,
            )
        )
    )
    return list(result.scalars().all())
