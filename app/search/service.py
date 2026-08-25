from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.items.models import Item


@dataclass
class SearchParams:
    q: str | None = None
    category_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    tag_id: uuid.UUID | None = None
    sort: str = "name_asc"
    page: int = 1
    per_page: int = 20


SORT_MAP = {
    "name_asc": (Item.name, True),
    "name_desc": (Item.name, False),
    "date_asc": (Item.created_at, True),
    "date_desc": (Item.created_at, False),
    "price_asc": (Item.purchase_price, True),
    "price_desc": (Item.purchase_price, False),
}


async def search_items(
    db: AsyncSession,
    params: SearchParams,
    access_filters: list | None = None,
) -> tuple[list[Item], int]:
    q = params.q.strip() if params.q else None

    query = select(Item)
    count_query = select(func.count()).select_from(Item)

    if q:
        pattern = f"%{q}%"
        search_filter = or_(
            Item.name.ilike(pattern),
            Item.description.ilike(pattern),
            Item.sku.ilike(pattern),
            Item.serial_number.ilike(pattern),
            Item.manufacturer.ilike(pattern),
            Item.model.ilike(pattern),
        )
        query = query.outerjoin(Item.tags).where(
            or_(search_filter, func.lower(cast(Item.id, String)) == q.lower())
        )
        count_query = count_query.outerjoin(Item.tags).where(
            or_(search_filter, func.lower(cast(Item.id, String)) == q.lower())
        )

    if params.category_id is not None:
        query = query.where(Item.category_id == params.category_id)
        count_query = count_query.where(Item.category_id == params.category_id)

    if params.location_id is not None:
        query = query.where(Item.location_id == params.location_id)
        count_query = count_query.where(Item.location_id == params.location_id)

    if params.tag_id is not None:
        from app.items.models import ItemTag

        query = query.join(ItemTag).where(ItemTag.tag_id == params.tag_id)
        count_query = count_query.join(ItemTag).where(ItemTag.tag_id == params.tag_id)

    if access_filters:
        for f in access_filters:
            query = query.where(f)
            count_query = count_query.where(f)

    total = (await db.execute(count_query)).scalar_one()

    sort_col, sort_asc = SORT_MAP.get(params.sort, (Item.name, True))
    order = sort_col.asc() if sort_asc else sort_col.desc()
    query = (
        query.distinct()
        .options(
            selectinload(Item.category),
            selectinload(Item.location),
            selectinload(Item.tags),
        )
        .order_by(order)
    )

    offset = (params.page - 1) * params.per_page
    query = query.offset(offset).limit(params.per_page)

    result = await db.execute(query)
    items = list(result.scalars().all())
    return items, total
