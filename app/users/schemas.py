from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str | None = None
    role: str = Field(default="viewer", pattern=r"^(admin|editor|viewer)$")


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = Field(default=None, pattern=r"^(admin|editor|viewer)$")
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    supabase_id: str
    email: str
    display_name: str | None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
