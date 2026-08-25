from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    parent_location_id: uuid.UUID | None = None


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    parent_location_id: uuid.UUID | None = None


class LocationResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    parent_location_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LocationTreeNode(BaseModel):
    id: uuid.UUID
    name: str
    children: list[LocationTreeNode] = []

    model_config = {"from_attributes": True}
