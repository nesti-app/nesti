from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.models import Category
from app.items.models import Item
from app.locations.models import Location
from app.tags.models import Tag


@dataclass
class DashboardStats:
    total_items: int
    total_categories: int
    total_locations: int
    total_tags: int
    items_without_image: int
    items_without_location: int
    items_without_category: int


async def get_dashboard_stats(db: AsyncSession) -> DashboardStats:
    count_q = select(func.count()).select_from
    total_items = (await db.execute(count_q(Item))).scalar_one()
    total_categories = (await db.execute(count_q(Category))).scalar_one()
    total_locations = (await db.execute(count_q(Location))).scalar_one()
    total_tags = (await db.execute(count_q(Tag))).scalar_one()

    from app.media.models import ItemImage

    items_with_image = (
        await db.execute(select(func.count(func.distinct(ItemImage.item_id))))
    ).scalar_one()
    items_with_location = (
        await db.execute(
            select(func.count()).select_from(Item).where(Item.location_id.isnot(None))
        )
    ).scalar_one()
    items_with_category = (
        await db.execute(
            select(func.count()).select_from(Item).where(Item.category_id.isnot(None))
        )
    ).scalar_one()

    return DashboardStats(
        total_items=total_items,
        total_categories=total_categories,
        total_locations=total_locations,
        total_tags=total_tags,
        items_without_image=total_items - items_with_image,
        items_without_location=total_items - items_with_location,
        items_without_category=total_items - items_with_category,
    )


async def get_recent_items(db: AsyncSession, limit: int = 10) -> list[Item]:
    result = await db.execute(select(Item).order_by(Item.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def get_recently_updated_items(db: AsyncSession, limit: int = 10) -> list[Item]:
    result = await db.execute(
        select(Item)
        .where(Item.updated_at.isnot(None))
        .order_by(Item.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
