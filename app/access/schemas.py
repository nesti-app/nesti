from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AccessScopeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class AccessScopeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class AccessScopeRuleCreate(BaseModel):
    rule_type: str = Field(pattern=r"^(location|category|tag|specific_item)$")
    rule_value: str = Field(min_length=1)


class AccessScopePermissionCreate(BaseModel):
    permission: str = Field(pattern=r"^(view|create|edit|move|delete|manage_images)$")


class AccessScopeUserCreate(BaseModel):
    user_id: uuid.UUID


class AccessScopeRuleResponse(BaseModel):
    id: uuid.UUID
    rule_type: str
    rule_value: str

    model_config = {"from_attributes": True}


class AccessScopePermissionResponse(BaseModel):
    id: uuid.UUID
    permission: str

    model_config = {"from_attributes": True}


class AccessScopeUserResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str = ""
    user_display_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AccessScopeResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    rules: list[AccessScopeRuleResponse] = []
    permissions: list[AccessScopePermissionResponse] = []
    users: list[AccessScopeUserResponse] = []

    model_config = {"from_attributes": True}


class AccessScopeDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    rules: list[AccessScopeRuleResponse] = []
    permissions: list[AccessScopePermissionResponse] = []
    users: list[AccessScopeUserResponse] = []
    matched_item_count: int = 0

    model_config = {"from_attributes": True}
