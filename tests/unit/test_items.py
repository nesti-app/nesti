from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.common.exceptions import ForbiddenError
from app.items import routes as items_routes
from app.items.schemas import (
    ItemAttributeCreate,
    ItemAttributeResponse,
    ItemAttributeUpdate,
    ItemCreate,
    ItemResponse,
    ItemUpdate,
)


def test_item_create_schema():
    data = ItemCreate(name="Power Drill")
    assert data.name == "Power Drill"
    assert data.description is None
    assert data.category_id is None
    assert data.tag_ids == []
    assert data.attributes == []


def test_item_create_full():
    data = ItemCreate(
        name="Laptop",
        description="Work laptop",
        category_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        manufacturer="Dell",
        model="XPS 15",
        serial_number="SN123",
        sku="SKU456",
        purchase_date=date(2024, 1, 15),
        purchase_price=Decimal("1299.99"),
        currency="USD",
        notes="Important",
    )
    assert data.manufacturer == "Dell"
    assert data.purchase_price == Decimal("1299.99")


def test_item_create_empty_name():
    with pytest.raises(ValidationError):
        ItemCreate(name="")


def test_item_update_all_optional():
    data = ItemUpdate()
    assert data.name is None
    assert data.manufacturer is None
    assert data.tag_ids is None
    assert data.attributes is None


def test_item_update_partial():
    data = ItemUpdate(name="New Name", manufacturer="New Mfr")
    assert data.name == "New Name"
    assert data.manufacturer == "New Mfr"
    assert data.model is None


def test_item_response_fields():
    resp = ItemResponse(
        id=uuid.uuid4(),
        name="Test Item",
        description=None,
        category_id=None,
        location_id=None,
        parent_item_id=None,
        manufacturer=None,
        model=None,
        serial_number=None,
        sku=None,
        purchase_date=None,
        purchase_price=None,
        currency=None,
        notes=None,
        created_by=None,
        updated_by=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert resp.name == "Test Item"
    assert resp.attributes == []


def test_attribute_create_schema():
    data = ItemAttributeCreate(name="Weight", value="2.5", unit="kg")
    assert data.name == "Weight"
    assert data.value == "2.5"
    assert data.unit == "kg"
    assert data.sort_order == 0


def test_attribute_create_empty_name():
    with pytest.raises(ValidationError):
        ItemAttributeCreate(name="", value="test")


def test_attribute_update_all_optional():
    data = ItemAttributeUpdate()
    assert data.name is None
    assert data.value is None
    assert data.unit is None
    assert data.sort_order is None


def test_attribute_response_fields():
    resp = ItemAttributeResponse(
        id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        name="Color",
        value="Red",
        unit=None,
        sort_order=0,
    )
    assert resp.name == "Color"
    assert resp.value == "Red"


async def test_check_item_permission_anonymous_uses_none_user(monkeypatch):
    captured = {}

    async def fake_has_permission(db, user_id, item_id, permission):
        captured["user_id"] = user_id
        captured["permission"] = permission
        return False

    monkeypatch.setattr(
        "app.access.service.user_has_item_permission", fake_has_permission
    )

    with pytest.raises(ForbiddenError):
        await items_routes._check_item_permission(None, None, uuid.uuid4(), "view")

    assert captured == {"user_id": None, "permission": "view"}


async def test_check_item_permission_anonymous_grants_view(monkeypatch):
    async def fake_has_permission(db, user_id, item_id, permission):
        return True

    monkeypatch.setattr(
        "app.access.service.user_has_item_permission", fake_has_permission
    )

    await items_routes._check_item_permission(None, None, uuid.uuid4(), "view")


async def test_get_user_item_filters_anonymous(monkeypatch):
    async def fake_anon(db):
        return []

    monkeypatch.setattr("app.access.service.evaluate_anonymous_scopes", fake_anon)

    filters = await items_routes._get_user_item_filters(None, None)
    # No public scopes → nothing is visible, not everything.
    assert len(filters) == 1
    assert type(filters[0]).__name__ == "False_"


async def test_get_user_item_filters_admin_is_unfiltered():
    admin = SimpleNamespace(role="admin", id=uuid.uuid4())
    filters = await items_routes._get_user_item_filters(None, admin)
    assert filters is None
