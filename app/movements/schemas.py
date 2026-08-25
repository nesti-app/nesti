from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MovementCreate(BaseModel):
    to_location_id: uuid.UUID | None = None
    reason: str | None = None
    notes: str | None = None


class MovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    from_location_id: uuid.UUID | None
    to_location_id: uuid.UUID | None
    moved_at: datetime
    moved_by: uuid.UUID | None
    reason: str | None
    notes: str | None

    from_location_name: str | None = None
    to_location_name: str | None = None
    moved_by_name: str | None = None
    moved_by_email: str | None = None
