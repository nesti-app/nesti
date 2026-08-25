from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ItemAttributeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=500)
    unit: str | None = None
    sort_order: int = 0


class ItemAttributeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    value: str | None = Field(default=None, min_length=1, max_length=500)
    unit: str | None = None
    sort_order: int | None = None


class ItemAttributeResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    name: str
    value: str
    unit: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    category_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    parent_item_id: uuid.UUID | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    sku: str | None = None
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    currency: str | None = None
    notes: str | None = None
    tag_ids: list[uuid.UUID] = []
    attributes: list[ItemAttributeCreate] = []


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    category_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    parent_item_id: uuid.UUID | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    sku: str | None = None
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    currency: str | None = None
    notes: str | None = None
    tag_ids: list[uuid.UUID] | None = None
    attributes: list[ItemAttributeCreate] | None = None


class ItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    category_id: uuid.UUID | None
    location_id: uuid.UUID | None
    parent_item_id: uuid.UUID | None
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    sku: str | None
    purchase_date: date | None
    purchase_price: Decimal | None
    currency: str | None
    notes: str | None
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    attributes: list[ItemAttributeResponse] = []

    model_config = {"from_attributes": True}
