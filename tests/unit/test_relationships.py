from __future__ import annotations

import uuid

import pytest

from app.relationships.schemas import (
    VALID_RELATIONSHIP_TYPES,
    RelationshipCreate,
    RelationshipResponse,
)


def test_relationship_create_schema():
    data = RelationshipCreate(
        target_item_id=uuid.uuid4(),
        relationship_type="contains",
    )
    assert data.relationship_type == "contains"
    assert data.target_item_id is not None


def test_relationship_create_all_valid_types():
    for rel_type in VALID_RELATIONSHIP_TYPES:
        data = RelationshipCreate(
            target_item_id=uuid.uuid4(),
            relationship_type=rel_type,
        )
        assert data.relationship_type == rel_type


def test_relationship_create_invalid_type():
    with pytest.raises(ValueError):
        RelationshipCreate(
            target_item_id=uuid.uuid4(),
            relationship_type="invalid_type",
        )


def test_relationship_response_fields():
    from datetime import UTC, datetime

    data = RelationshipResponse(
        id=uuid.uuid4(),
        source_item_id=uuid.uuid4(),
        target_item_id=uuid.uuid4(),
        relationship_type="part_of",
        created_at=datetime.now(UTC),
        created_by=None,
        target_item_name="SSD Drive",
        target_item_id_short="A7F3",
    )
    assert data.relationship_type == "part_of"
    assert data.target_item_name == "SSD Drive"
    assert data.target_item_id_short == "A7F3"


def test_relationship_response_optional_fields():
    from datetime import UTC, datetime

    data = RelationshipResponse(
        id=uuid.uuid4(),
        source_item_id=uuid.uuid4(),
        target_item_id=uuid.uuid4(),
        relationship_type="related_to",
        created_at=datetime.now(UTC),
        created_by=None,
    )
    assert data.target_item_name is None
    assert data.target_item_id_short is None
