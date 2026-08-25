from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.access.schemas import (
    AccessScopeCreate,
    AccessScopeDetailResponse,
    AccessScopePermissionCreate,
    AccessScopePermissionResponse,
    AccessScopeResponse,
    AccessScopeRuleCreate,
    AccessScopeRuleResponse,
    AccessScopeUpdate,
    AccessScopeUserCreate,
    AccessScopeUserResponse,
)


def test_scope_create_schema():
    data = AccessScopeCreate(name="Garage Tools", description="Tools in garage")
    assert data.name == "Garage Tools"
    assert data.description == "Tools in garage"


def test_scope_create_no_description():
    data = AccessScopeCreate(name="Server Room")
    assert data.description is None


def test_scope_update_all_optional():
    data = AccessScopeUpdate()
    assert data.name is None
    assert data.description is None


def test_scope_update_partial():
    data = AccessScopeUpdate(name="New Name")
    assert data.name == "New Name"
    assert data.description is None


def test_rule_create_valid_types():
    for rt in ["location", "category", "tag", "specific_item"]:
        data = AccessScopeRuleCreate(rule_type=rt, rule_value="test-value")
        assert data.rule_type == rt


def test_rule_create_invalid_type():
    with pytest.raises(ValidationError):
        AccessScopeRuleCreate(rule_type="invalid", rule_value="test")


def test_permission_create_valid():
    for perm in ["view", "create", "edit", "move", "delete", "manage_images"]:
        data = AccessScopePermissionCreate(permission=perm)
        assert data.permission == perm


def test_permission_create_invalid():
    with pytest.raises(ValidationError):
        AccessScopePermissionCreate(permission="admin")


def test_user_create_schema():
    uid = uuid.uuid4()
    data = AccessScopeUserCreate(user_id=uid)
    assert data.user_id == uid


def test_scope_response_fields():
    resp = AccessScopeResponse(
        id=uuid.uuid4(),
        name="Test Scope",
        description="desc",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert resp.name == "Test Scope"
    assert resp.rules == []
    assert resp.permissions == []
    assert resp.users == []


def test_rule_response_fields():
    resp = AccessScopeRuleResponse(id=uuid.uuid4(), rule_type="location", rule_value="garage")
    assert resp.rule_type == "location"
    assert resp.rule_value == "garage"


def test_permission_response_fields():
    resp = AccessScopePermissionResponse(id=uuid.uuid4(), permission="view")
    assert resp.permission == "view"


def test_user_response_fields():
    resp = AccessScopeUserResponse(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        user_email="test@example.com",
        user_display_name="Test User",
        created_at=datetime.now(UTC),
    )
    assert resp.user_email == "test@example.com"
    assert resp.user_display_name == "Test User"


def test_detail_response_includes_count():
    resp = AccessScopeDetailResponse(
        id=uuid.uuid4(),
        name="Detail Scope",
        description=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        matched_item_count=42,
    )
    assert resp.matched_item_count == 42
