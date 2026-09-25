from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.access import service as access_service
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


def test_scope_create_anonymous_flag():
    assert AccessScopeCreate(name="Public").allow_anonymous is False
    assert AccessScopeCreate(name="Public", allow_anonymous=True).allow_anonymous is True


def test_scope_update_anonymous_flag_optional():
    assert AccessScopeUpdate().allow_anonymous is None
    assert AccessScopeUpdate(allow_anonymous=True).allow_anonymous is True


def test_scope_response_includes_anonymous_flag():
    resp = AccessScopeResponse(
        id=uuid.uuid4(),
        name="Public Scope",
        description=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        allow_anonymous=True,
    )
    assert resp.allow_anonymous is True


def test_allowed_permission_anonymous_only_view():
    assert access_service._allowed_permission(None, "view") is True
    assert access_service._allowed_permission(None, "edit") is False
    assert access_service._allowed_permission(None, "delete") is False
    assert access_service._allowed_permission(uuid.uuid4(), "edit") is True


async def test_scopes_for_user_uses_anonymous_when_none(monkeypatch):
    calls = {"anon": 0, "user": 0}

    async def fake_anon(db):
        calls["anon"] += 1
        return []

    async def fake_user(db, uid):
        calls["user"] += 1
        return []

    monkeypatch.setattr(access_service, "evaluate_anonymous_scopes", fake_anon)
    monkeypatch.setattr(access_service, "evaluate_user_scopes", fake_user)

    assert await access_service._scopes_for_user(None, None) == []
    assert calls == {"anon": 1, "user": 0}


async def test_anonymous_cannot_get_non_view_permission():
    result = await access_service.user_has_item_permission(None, None, uuid.uuid4(), "edit")
    assert result is False


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
