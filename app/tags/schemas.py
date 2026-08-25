from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class TagResponse(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}
