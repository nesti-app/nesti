from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.items.models import Item, ItemAttribute
from app.items.schemas import (
    ItemAttributeCreate,
    ItemAttributeUpdate,
    ItemCreate,
    ItemUpdate,
)
from app.tags.models import ItemTag


async def list_items(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 100,
    filters: list | None = None,
) -> tuple[list[Item], int]:
    base = select(func.count()).select_from(Item)
    if filters:
        base = base.where(and_(*filters))
    count_result = await db.execute(base)
    total = count_result.scalar_one()

    query = select(Item)
    if filters:
        query = query.where(and_(*filters))
    offset = (page - 1) * per_page
    result = await db.execute(query.order_by(Item.name).offset(offset).limit(per_page))
    return list(result.scalars().all()), total


async def get_item_by_id(db: AsyncSession, item_id: uuid.UUID) -> Item:
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError("Item not found")
    return item


async def create_item(
    db: AsyncSession,
    data: ItemCreate,
    *,
    user_id: uuid.UUID | None = None,
) -> Item:
    item = Item(
        name=data.name,
        description=data.description,
        category_id=data.category_id,
        location_id=data.location_id,
        parent_item_id=data.parent_item_id,
        manufacturer=data.manufacturer,
        model=data.model,
        serial_number=data.serial_number,
        sku=data.sku,
        purchase_date=data.purchase_date,
        purchase_price=data.purchase_price,
        currency=data.currency,
        notes=data.notes,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(item)
    await db.flush()

    for tag_id in data.tag_ids:
        db.add(ItemTag(item_id=item.id, tag_id=tag_id))

    for idx, attr_data in enumerate(data.attributes):
        attr = ItemAttribute(
            item_id=item.id,
            name=attr_data.name,
            value=attr_data.value,
            unit=attr_data.unit,
            sort_order=attr_data.sort_order if attr_data.sort_order else idx,
        )
        db.add(attr)

    await db.flush()
    await db.refresh(item)
    return item


async def update_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    data: ItemUpdate,
    *,
    user_id: uuid.UUID | None = None,
) -> Item:
    item = await get_item_by_id(db, item_id)

    update_data = data.model_dump(exclude_unset=True, exclude={"tag_ids", "attributes"})
    update_data["updated_by"] = user_id
    for field, value in update_data.items():
        setattr(item, field, value)

    if data.tag_ids is not None:
        await db.execute(ItemTag.__table__.delete().where(ItemTag.item_id == item_id))
        for tag_id in data.tag_ids:
            db.add(ItemTag(item_id=item_id, tag_id=tag_id))

    if data.attributes is not None:
        await db.execute(
            ItemAttribute.__table__.delete().where(ItemAttribute.item_id == item_id)
        )
        for idx, attr_data in enumerate(data.attributes):
            attr = ItemAttribute(
                item_id=item_id,
                name=attr_data.name,
                value=attr_data.value,
                unit=attr_data.unit,
                sort_order=attr_data.sort_order if attr_data.sort_order else idx,
            )
            db.add(attr)

    await db.flush()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item_id: uuid.UUID) -> None:
    item = await get_item_by_id(db, item_id)
    await db.delete(item)
    await db.flush()


async def list_item_attributes(
    db: AsyncSession,
    item_id: uuid.UUID,
) -> list[ItemAttribute]:
    result = await db.execute(
        select(ItemAttribute)
        .where(ItemAttribute.item_id == item_id)
        .order_by(ItemAttribute.sort_order)
    )
    return list(result.scalars().all())


async def create_item_attribute(
    db: AsyncSession,
    item_id: uuid.UUID,
    data: ItemAttributeCreate,
) -> ItemAttribute:
    await get_item_by_id(db, item_id)
    attr = ItemAttribute(
        item_id=item_id,
        name=data.name,
        value=data.value,
        unit=data.unit,
        sort_order=data.sort_order,
    )
    db.add(attr)
    await db.flush()
    await db.refresh(attr)
    return attr


async def update_item_attribute(
    db: AsyncSession,
    attribute_id: uuid.UUID,
    data: ItemAttributeUpdate,
) -> ItemAttribute:
    result = await db.execute(select(ItemAttribute).where(ItemAttribute.id == attribute_id))
    attr = result.scalar_one_or_none()
    if attr is None:
        raise NotFoundError("Attribute not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(attr, field, value)

    await db.flush()
    await db.refresh(attr)
    return attr


async def delete_item_attribute(
    db: AsyncSession,
    attribute_id: uuid.UUID,
) -> None:
    result = await db.execute(select(ItemAttribute).where(ItemAttribute.id == attribute_id))
    attr = result.scalar_one_or_none()
    if attr is None:
        raise NotFoundError("Attribute not found")
    await db.delete(attr)
    await db.flush()
