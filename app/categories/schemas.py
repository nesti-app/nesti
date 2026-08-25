from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    parent_category_id: uuid.UUID | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(
        default=None, min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$"
    )
    description: str | None = None
    parent_category_id: uuid.UUID | None = None


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    parent_category_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoryTreeNode(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    children: list[CategoryTreeNode] = []

    model_config = {"from_attributes": True}
