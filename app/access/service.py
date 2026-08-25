from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.access.models import (
    AccessScope,
    AccessScopePermission,
    AccessScopeRule,
    AccessScopeUser,
)
from app.access.schemas import (
    AccessScopeCreate,
    AccessScopePermissionCreate,
    AccessScopeRuleCreate,
    AccessScopeUpdate,
    AccessScopeUserCreate,
)
from app.common.exceptions import ConflictError, NotFoundError
from app.items.models import Item
from app.tags.models import ItemTag
from app.users.models import User

VALID_RULE_TYPES = {"location", "category", "tag", "specific_item"}
VALID_PERMISSIONS = {"view", "create", "edit", "move", "delete", "manage_images"}


async def list_scopes(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 100,
) -> tuple[list[AccessScope], int]:
    count_result = await db.execute(select(func.count()).select_from(AccessScope))
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(AccessScope).order_by(AccessScope.name).offset(offset).limit(per_page)
    )
    return list(result.scalars().all()), total


async def get_scope_by_id(db: AsyncSession, scope_id: uuid.UUID) -> AccessScope:
    result = await db.execute(select(AccessScope).where(AccessScope.id == scope_id))
    scope = result.scalar_one_or_none()
    if scope is None:
        raise NotFoundError("Access Scope not found")
    return scope


async def create_scope(db: AsyncSession, data: AccessScopeCreate) -> AccessScope:
    scope = AccessScope(name=data.name, description=data.description)
    db.add(scope)
    await db.flush()
    await db.refresh(scope)
    return scope


async def update_scope(
    db: AsyncSession,
    scope_id: uuid.UUID,
    data: AccessScopeUpdate,
) -> AccessScope:
    scope = await get_scope_by_id(db, scope_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scope, field, value)
    await db.flush()
    await db.refresh(scope)
    return scope


async def delete_scope(db: AsyncSession, scope_id: uuid.UUID) -> None:
    scope = await get_scope_by_id(db, scope_id)
    await db.delete(scope)
    await db.flush()


async def add_rule(
    db: AsyncSession,
    scope_id: uuid.UUID,
    data: AccessScopeRuleCreate,
) -> AccessScopeRule:
    await get_scope_by_id(db, scope_id)

    if data.rule_type not in VALID_RULE_TYPES:
        raise ConflictError(f"Invalid rule type: {data.rule_type}")

    existing = await db.execute(
        select(AccessScopeRule).where(
            AccessScopeRule.scope_id == scope_id,
            AccessScopeRule.rule_type == data.rule_type,
            AccessScopeRule.rule_value == data.rule_value,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Rule already exists for this scope")

    rule = AccessScopeRule(
        scope_id=scope_id,
        rule_type=data.rule_type,
        rule_value=data.rule_value,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


async def remove_rule(
    db: AsyncSession,
    scope_id: uuid.UUID,
    rule_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(AccessScopeRule).where(
            AccessScopeRule.id == rule_id,
            AccessScopeRule.scope_id == scope_id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise NotFoundError("Rule not found")
    await db.delete(rule)
    await db.flush()


async def add_permission(
    db: AsyncSession,
    scope_id: uuid.UUID,
    data: AccessScopePermissionCreate,
) -> AccessScopePermission:
    await get_scope_by_id(db, scope_id)

    if data.permission not in VALID_PERMISSIONS:
        raise ConflictError(f"Invalid permission: {data.permission}")

    existing = await db.execute(
        select(AccessScopePermission).where(
            AccessScopePermission.scope_id == scope_id,
            AccessScopePermission.permission == data.permission,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Permission already exists for this scope")

    perm = AccessScopePermission(
        scope_id=scope_id,
        permission=data.permission,
    )
    db.add(perm)
    await db.flush()
    await db.refresh(perm)
    return perm


async def remove_permission(
    db: AsyncSession,
    scope_id: uuid.UUID,
    permission_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(AccessScopePermission).where(
            AccessScopePermission.id == permission_id,
            AccessScopePermission.scope_id == scope_id,
        )
    )
    perm = result.scalar_one_or_none()
    if perm is None:
        raise NotFoundError("Permission not found")
    await db.delete(perm)
    await db.flush()


async def assign_user(
    db: AsyncSession,
    scope_id: uuid.UUID,
    data: AccessScopeUserCreate,
) -> AccessScopeUser:
    await get_scope_by_id(db, scope_id)

    user_result = await db.execute(select(User).where(User.id == data.user_id))
    if user_result.scalar_one_or_none() is None:
        raise NotFoundError("User not found")

    existing = await db.execute(
        select(AccessScopeUser).where(
            AccessScopeUser.scope_id == scope_id,
            AccessScopeUser.user_id == data.user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("User already assigned to this scope")

    su = AccessScopeUser(scope_id=scope_id, user_id=data.user_id)
    db.add(su)
    await db.flush()
    await db.refresh(su)
    return su


async def remove_user(
    db: AsyncSession,
    scope_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(AccessScopeUser).where(
            AccessScopeUser.scope_id == scope_id,
            AccessScopeUser.user_id == user_id,
        )
    )
    su = result.scalar_one_or_none()
    if su is None:
        raise NotFoundError("User assignment not found")
    await db.delete(su)
    await db.flush()


async def _resolve_rule_value(
    db: AsyncSession,
    rule_type: str,
    rule_value: str,
) -> uuid.UUID | None:
    """Resolve a rule value to an entity UUID. Tries UUID first, then slug lookup."""
    try:
        return uuid.UUID(rule_value)
    except ValueError:
        pass

    if rule_type == "location":
        from app.locations.models import Location

        result = await db.execute(select(Location.id).where(Location.slug == rule_value))
        return result.scalar_one_or_none()

    if rule_type == "category":
        from app.categories.models import Category

        result = await db.execute(select(Category.id).where(Category.slug == rule_value))
        return result.scalar_one_or_none()

    return None


async def _build_item_filters(
    db: AsyncSession,
    rules: list[AccessScopeRule],
) -> list:
    """Build SQLAlchemy filter conditions from scope rules (AND semantics)."""
    conditions = []
    for rule in rules:
        if rule.rule_type == "location":
            resolved = await _resolve_rule_value(db, "location", rule.rule_value)
            if resolved is not None:
                conditions.append(Item.location_id == resolved)
        elif rule.rule_type == "category":
            resolved = await _resolve_rule_value(db, "category", rule.rule_value)
            if resolved is not None:
                conditions.append(Item.category_id == resolved)
        elif rule.rule_type == "tag":
            conditions.append(
                Item.id.in_(select(ItemTag.item_id).where(ItemTag.tag_id == rule.rule_value))
            )
        elif rule.rule_type == "specific_item":
            try:
                item_uuid = uuid.UUID(rule.rule_value)
                conditions.append(Item.id == item_uuid)
            except ValueError:
                pass
    return conditions


async def count_matching_items(
    db: AsyncSession,
    scope_id: uuid.UUID,
) -> int:
    scope = await get_scope_by_id(db, scope_id)
    if not scope.rules:
        return 0

    conditions = await _build_item_filters(db, scope.rules)
    if not conditions:
        return 0

    query = select(func.count()).select_from(Item).where(and_(*conditions))
    result = await db.execute(query)
    return result.scalar_one()


async def evaluate_user_scopes(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[AccessScope]:
    """Get all scopes assigned to a user."""
    result = await db.execute(
        select(AccessScope)
        .join(AccessScopeUser, AccessScopeUser.scope_id == AccessScope.id)
        .where(AccessScopeUser.user_id == user_id)
    )
    return list(result.scalars().all())


async def user_has_item_permission(
    db: AsyncSession,
    user_id: uuid.UUID,
    item_id: uuid.UUID,
    permission: str,
) -> bool:
    """Check if a user has a specific permission on a specific item.

    The item must match ALL rules of at least one scope that:
    1. Is assigned to the user
    2. Grants the requested permission
    """
    scopes = await evaluate_user_scopes(db, user_id)
    if not scopes:
        return False

    for scope in scopes:
        scope_perms = {p.permission for p in scope.permissions}
        if permission not in scope_perms:
            continue

        conditions = await _build_item_filters(db, scope.rules)
        if not conditions:
            continue

        query = (
            select(func.count()).select_from(Item).where(and_(Item.id == item_id, *conditions))
        )
        result = await db.execute(query)
        count = result.scalar_one()
        if count > 0:
            return True

    return False


async def get_user_item_permissions(
    db: AsyncSession,
    user_id: uuid.UUID,
    item_id: uuid.UUID,
) -> set[str]:
    """Get all permissions a user has on a specific item."""
    scopes = await evaluate_user_scopes(db, user_id)
    merged: set[str] = set()

    for scope in scopes:
        conditions = await _build_item_filters(db, scope.rules)
        if not conditions:
            continue

        query = (
            select(func.count()).select_from(Item).where(and_(Item.id == item_id, *conditions))
        )
        result = await db.execute(query)
        count = result.scalar_one()
        if count > 0:
            merged.update(p.permission for p in scope.permissions)

    return merged
