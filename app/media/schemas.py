from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    storage_path: str
    mime_type: str
    width: int | None
    height: int | None
    size_bytes: int | None
    sort_order: int
    is_primary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ImageReorderItem(BaseModel):
    id: uuid.UUID
    sort_order: int
