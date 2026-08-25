from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

VALID_RELATIONSHIP_TYPES = {
    "contains",
    "part_of",
    "accessory_of",
    "connected_to",
    "used_with",
    "replacement_for",
    "related_to",
}


class RelationshipCreate(BaseModel):
    target_item_id: uuid.UUID
    relationship_type: str

    @field_validator("relationship_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_RELATIONSHIP_TYPES:
            msg = f"Invalid type. Must be one of: {', '.join(sorted(VALID_RELATIONSHIP_TYPES))}"
            raise ValueError(msg)
        return v


class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_item_id: uuid.UUID
    target_item_id: uuid.UUID
    relationship_type: str
    created_at: datetime
    created_by: uuid.UUID | None

    target_item_name: str | None = None
    target_item_id_short: str | None = None
