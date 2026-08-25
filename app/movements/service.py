from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.exceptions import NotFoundError
from app.items.models import Item, ItemMovement
from app.locations.service import get_location_by_id


async def get_item_by_id_for_move(db: AsyncSession, item_id: uuid.UUID) -> Item:
    result = await db.execute(
        select(Item).where(Item.id == item_id).options(selectinload(Item.location))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError("Item not found")
    return item


async def move_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    to_location_id: uuid.UUID | None,
    reason: str | None,
    notes: str | None,
    user_id: uuid.UUID,
) -> ItemMovement:
    item = await get_item_by_id_for_move(db, item_id)

    if to_location_id is not None:
        await get_location_by_id(db, to_location_id)

    from_location_id = item.location_id

    if to_location_id is not None and from_location_id == to_location_id:
        from_location_id = from_location_id

    movement = ItemMovement(
        item_id=item.id,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        moved_by=user_id,
        reason=reason,
        notes=notes,
    )
    db.add(movement)

    item.location_id = to_location_id
    item.updated_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(movement)
    return movement


async def get_item_movements(
    db: AsyncSession,
    item_id: uuid.UUID,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[ItemMovement], int]:
    count_q = (
        select(func.count()).select_from(ItemMovement).where(ItemMovement.item_id == item_id)
    )
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * per_page
    q = (
        select(ItemMovement)
        .where(ItemMovement.item_id == item_id)
        .options(
            selectinload(ItemMovement.from_location),
            selectinload(ItemMovement.to_location),
            selectinload(ItemMovement.moved_by_user),
        )
        .order_by(ItemMovement.moved_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(q)
    movements = list(result.scalars().all())
    return movements, total


async def get_movement_by_id(
    db: AsyncSession,
    movement_id: uuid.UUID,
) -> ItemMovement:
    result = await db.execute(
        select(ItemMovement)
        .where(ItemMovement.id == movement_id)
        .options(
            selectinload(ItemMovement.from_location),
            selectinload(ItemMovement.to_location),
            selectinload(ItemMovement.moved_by_user),
        )
    )
    movement = result.scalar_one_or_none()
    if movement is None:
        raise NotFoundError("Movement not found")
    return movement
