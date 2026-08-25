from __future__ import annotations

import uuid

from app.movements.schemas import MovementCreate, MovementResponse


def test_movement_create_schema():
    data = MovementCreate(
        to_location_id=uuid.uuid4(),
        reason="Зміна кімнати",
        notes="Перенесено на полицю",
    )
    assert data.to_location_id is not None
    assert data.reason == "Зміна кімнати"
    assert data.notes == "Перенесено на полицю"


def test_movement_create_minimal():
    data = MovementCreate()
    assert data.to_location_id is None
    assert data.reason is None
    assert data.notes is None


def test_movement_response_fields():
    from datetime import UTC, datetime

    data = MovementResponse(
        id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        from_location_id=uuid.uuid4(),
        to_location_id=uuid.uuid4(),
        moved_at=datetime.now(UTC),
        moved_by=uuid.uuid4(),
        reason="Ремонт",
        notes="Тимчасово",
        from_location_name="Кухня",
        to_location_name="Гардеробна",
        moved_by_name="Олексій",
        moved_by_email="alex@test.com",
    )
    assert data.from_location_name == "Кухня"
    assert data.to_location_name == "Гардеробна"
    assert data.moved_by_name == "Олексій"
    assert data.moved_by_email == "alex@test.com"
    assert data.reason == "Ремонт"


def test_movement_response_optional_fields():
    from datetime import UTC, datetime

    data = MovementResponse(
        id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        from_location_id=None,
        to_location_id=uuid.uuid4(),
        moved_at=datetime.now(UTC),
        moved_by=None,
        reason=None,
        notes=None,
    )
    assert data.from_location_id is None
    assert data.from_location_name is None
    assert data.to_location_name is None
    assert data.moved_by_name is None
