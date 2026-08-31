from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.models import Category
from app.items.models import Item, ItemAttribute, ItemMovement, ItemRelationship
from app.locations.models import Location
from app.media.models import ItemImage
from app.tags.models import Tag

SCHEMA_VERSION = "1.0"


async def export_inventory(db: AsyncSession) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "format": "nesti-backup",
            "schema_version": SCHEMA_VERSION,
            "created_at": datetime.now(UTC).isoformat(),
            "application_version": "0.1.0",
            "image_format": "webp",
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        items = list((await db.execute(select(Item))).scalars().all())
        zf.writestr(
            "items.json",
            json.dumps([_item_to_dict(i) for i in items], indent=2),
        )

        cats = list((await db.execute(select(Category))).scalars().all())
        zf.writestr(
            "categories.json",
            json.dumps([_cat_to_dict(c) for c in cats], indent=2),
        )

        tags = list((await db.execute(select(Tag))).scalars().all())
        tag_data = [{"id": str(t.id), "name": t.name} for t in tags]
        zf.writestr("tags.json", json.dumps(tag_data, indent=2))

        locs = list((await db.execute(select(Location))).scalars().all())
        zf.writestr(
            "locations.json",
            json.dumps([_loc_to_dict(loc) for loc in locs], indent=2),
        )

        attrs = list((await db.execute(select(ItemAttribute))).scalars().all())
        zf.writestr(
            "item_attributes.json",
            json.dumps([_attr_to_dict(a) for a in attrs], indent=2),
        )

        rels = list((await db.execute(select(ItemRelationship))).scalars().all())
        zf.writestr(
            "item_relationships.json",
            json.dumps([_rel_to_dict(r) for r in rels], indent=2),
        )

        movements = list((await db.execute(select(ItemMovement))).scalars().all())
        zf.writestr(
            "item_movements.json",
            json.dumps([_mov_to_dict(mv) for mv in movements], indent=2),
        )

        images = list((await db.execute(select(ItemImage))).scalars().all())
        zf.writestr(
            "item_images.json",
            json.dumps([_img_to_dict(img) for img in images], indent=2),
        )

        if images:
            from app.media.storage import get_storage_backend

            backend = get_storage_backend()
            for img in images:
                try:
                    data = await backend.download(img.storage_path)
                    zf.writestr(f"images/{img.storage_path}", data)
                except Exception:
                    pass

    return buf.getvalue()


def _item_to_dict(item: Item) -> dict:
    return {
        "id": str(item.id),
        "name": item.name,
        "description": item.description,
        "category_id": (str(item.category_id) if item.category_id else None),
        "location_id": (str(item.location_id) if item.location_id else None),
        "parent_item_id": (str(item.parent_item_id) if item.parent_item_id else None),
        "manufacturer": item.manufacturer,
        "model": item.model,
        "serial_number": item.serial_number,
        "sku": item.sku,
        "purchase_date": (item.purchase_date.isoformat() if item.purchase_date else None),
        "purchase_price": (str(item.purchase_price) if item.purchase_price else None),
        "currency": item.currency,
        "notes": item.notes,
        "created_by": (str(item.created_by) if item.created_by else None),
    }


def _cat_to_dict(cat: Category) -> dict:
    return {
        "id": str(cat.id),
        "name": cat.name,
        "slug": cat.slug,
        "description": cat.description,
        "parent_category_id": (str(cat.parent_category_id) if cat.parent_category_id else None),
    }


def _loc_to_dict(loc: Location) -> dict:
    return {
        "id": str(loc.id),
        "name": loc.name,
        "description": loc.description,
        "parent_location_id": (str(loc.parent_location_id) if loc.parent_location_id else None),
    }


def _attr_to_dict(attr: ItemAttribute) -> dict:
    return {
        "id": str(attr.id),
        "item_id": str(attr.item_id),
        "name": attr.name,
        "value": attr.value,
        "unit": attr.unit,
        "sort_order": attr.sort_order,
    }


def _rel_to_dict(rel: ItemRelationship) -> dict:
    return {
        "id": str(rel.id),
        "source_item_id": str(rel.source_item_id),
        "target_item_id": str(rel.target_item_id),
        "relationship_type": rel.relationship_type,
        "created_by": (str(rel.created_by) if rel.created_by else None),
    }


def _mov_to_dict(mov: ItemMovement) -> dict:
    return {
        "id": str(mov.id),
        "item_id": str(mov.item_id),
        "from_location_id": (str(mov.from_location_id) if mov.from_location_id else None),
        "to_location_id": (str(mov.to_location_id) if mov.to_location_id else None),
        "moved_at": (mov.moved_at.isoformat() if mov.moved_at else None),
        "moved_by": (str(mov.moved_by) if mov.moved_by else None),
        "reason": mov.reason,
        "notes": mov.notes,
    }


def _img_to_dict(img: ItemImage) -> dict:
    return {
        "id": str(img.id),
        "item_id": str(img.item_id),
        "storage_path": img.storage_path,
        "mime_type": img.mime_type,
        "width": img.width,
        "height": img.height,
        "size_bytes": img.size_bytes,
        "sort_order": img.sort_order,
        "is_primary": img.is_primary,
    }
