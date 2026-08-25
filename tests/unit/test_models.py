from __future__ import annotations

from app.access.models import (
    AccessScope,
    AccessScopePermission,
    AccessScopeRule,
    AccessScopeUser,
)
from app.categories.models import Category
from app.db.base import Base
from app.items.models import Item, ItemAttribute, ItemMovement, ItemRelationship
from app.locations.models import Location
from app.media.models import ItemImage
from app.tags.models import ItemTag, Tag
from app.users.models import User

EXPECTED_TABLES = {
    "users",
    "items",
    "categories",
    "tags",
    "item_tags",
    "locations",
    "item_attributes",
    "item_relationships",
    "item_movements",
    "item_images",
    "access_scopes",
    "access_scope_rules",
    "access_scope_permissions",
    "access_scope_users",
}


def test_all_models_importable() -> None:
    assert User is not None
    assert Item is not None
    assert Category is not None
    assert Tag is not None
    assert Location is not None
    assert ItemTag is not None
    assert ItemAttribute is not None
    assert ItemRelationship is not None
    assert ItemMovement is not None
    assert ItemImage is not None
    assert AccessScope is not None
    assert AccessScopeRule is not None
    assert AccessScopePermission is not None
    assert AccessScopeUser is not None


def test_metadata_contains_all_tables() -> None:
    table_names = set(Base.metadata.tables.keys())
    assert EXPECTED_TABLES.issubset(table_names), (
        f"Missing tables: {EXPECTED_TABLES - table_names}"
    )


def test_item_table_columns() -> None:
    table = Base.metadata.tables["items"]
    column_names = {c.name for c in table.columns}
    expected = {
        "id",
        "name",
        "description",
        "category_id",
        "location_id",
        "parent_item_id",
        "manufacturer",
        "model",
        "serial_number",
        "sku",
        "purchase_date",
        "purchase_price",
        "currency",
        "notes",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    }
    assert expected.issubset(column_names)
