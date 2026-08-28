from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.categories.schemas import CategoryCreate, CategoryResponse, CategoryUpdate
from app.locations.schemas import LocationCreate, LocationResponse, LocationUpdate
from app.tags.schemas import TagCreate, TagResponse, TagUpdate


def test_category_create_schema():
    data = CategoryCreate(name="Kitchen")
    assert data.name == "Kitchen"
    assert data.description is None
    assert data.parent_category_id is None


def test_category_create_with_parent():
    pid = uuid.uuid4()
    data = CategoryCreate(
        name="Appliances",
        parent_category_id=pid,
    )
    assert data.parent_category_id == pid


def test_category_update_all_optional():
    data = CategoryUpdate()
    assert data.name is None
    assert data.description is None
    assert data.parent_category_id is None


def test_category_response_fields():
    resp = CategoryResponse(
        id=uuid.uuid4(),
        name="Test",
        description="desc",
        parent_category_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert resp.name == "Test"


def test_tag_create_schema():
    data = TagCreate(name="Important")
    assert data.name == "Important"


def test_tag_update_optional():
    data = TagUpdate()
    assert data.name is None


def test_tag_response_fields():
    resp = TagResponse(id=uuid.uuid4(), name="Urgent")
    assert resp.name == "Urgent"


def test_location_create_schema():
    data = LocationCreate(name="Living Room")
    assert data.name == "Living Room"
    assert data.description is None
    assert data.parent_location_id is None


def test_location_create_with_parent():
    pid = uuid.uuid4()
    data = LocationCreate(name="Shelf A", parent_location_id=pid)
    assert data.parent_location_id == pid


def test_location_update_all_optional():
    data = LocationUpdate()
    assert data.name is None
    assert data.description is None
    assert data.parent_location_id is None


def test_location_response_fields():
    resp = LocationResponse(
        id=uuid.uuid4(),
        name="Bedroom",
        description=None,
        parent_location_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert resp.name == "Bedroom"
