from __future__ import annotations

import json
import zipfile
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

from app.backup.service import (
    SCHEMA_VERSION,
    _cat_to_dict,
    _item_to_dict,
    export_inventory,
)
from app.categories.models import Category
from app.items.models import Item


def test_schema_version():
    assert SCHEMA_VERSION == "1.0"


def test_item_to_dict():
    item = MagicMock(spec=Item)
    item.id = None
    item.name = "Test Item"
    item.description = "A test"
    item.category_id = None
    item.location_id = None
    item.parent_item_id = None
    item.manufacturer = "ACME"
    item.model = "X1"
    item.serial_number = "SN123"
    item.sku = "SKU001"
    item.purchase_date = date(2025, 1, 15)
    item.purchase_price = Decimal("99.99")
    item.currency = "UAH"
    item.notes = "Some notes"
    item.created_by = None

    d = _item_to_dict(item)
    assert d["name"] == "Test Item"
    assert d["manufacturer"] == "ACME"
    assert d["purchase_date"] == "2025-01-15"
    assert d["purchase_price"] == "99.99"
    assert d["currency"] == "UAH"


def test_cat_to_dict():
    cat = MagicMock(spec=Category)
    cat.id = None
    cat.name = "Electronics"
    cat.slug = "electronics"
    cat.description = "Electronic devices"
    cat.parent_category_id = None

    d = _cat_to_dict(cat)
    assert d["name"] == "Electronics"
    assert d["slug"] == "electronics"
    assert d["parent_category_id"] is None


async def test_export_inventory_produces_zip():
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute.return_value = mock_result

    data = await export_inventory(db)
    assert len(data) > 0

    with zipfile.ZipFile(BytesIO(data), "r") as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "items.json" in names
        assert "categories.json" in names
        assert "tags.json" in names
        assert "locations.json" in names
        assert "item_attributes.json" in names
        assert "item_relationships.json" in names
        assert "item_movements.json" in names

        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["format"] == "nesti-backup"
        assert manifest["schema_version"] == SCHEMA_VERSION
