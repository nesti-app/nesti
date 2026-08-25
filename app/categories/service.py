from __future__ import annotations

import uuid
from re import sub

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.categories.models import Category
from app.categories.schemas import CategoryCreate, CategoryUpdate
from app.common.exceptions import ConflictError, NotFoundError


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = sub(r"[^\w\s-]", "", text)
    text = sub(r"[\s_]+", "-", text)
    text = sub(r"-+", "-", text)
    return text.strip("-")


async def list_categories(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 100,
) -> tuple[list[Category], int]:
    """List all categories with pagination."""
    count_result = await db.execute(select(func.count()).select_from(Category))
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Category).order_by(Category.name).offset(offset).limit(per_page)
    )
    return list(result.scalars().all()), total


async def get_category_by_id(db: AsyncSession, category_id: uuid.UUID) -> Category:
    """Get a category by ID."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise NotFoundError("Category not found")
    return category


async def get_category_by_slug(db: AsyncSession, slug: str) -> Category:
    """Get a category by slug."""
    result = await db.execute(select(Category).where(Category.slug == slug))
    category = result.scalar_one_or_none()
    if category is None:
        raise NotFoundError("Category not found")
    return category


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    """Create a new category."""
    existing = await db.execute(select(Category).where(Category.slug == data.slug))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Category with this slug already exists")

    if data.parent_category_id is not None:
        await get_category_by_id(db, data.parent_category_id)

    category = Category(
        name=data.name,
        slug=data.slug,
        description=data.description,
        parent_category_id=data.parent_category_id,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession,
    category_id: uuid.UUID,
    data: CategoryUpdate,
) -> Category:
    """Update a category."""
    category = await get_category_by_id(db, category_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.flush()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: uuid.UUID) -> None:
    """Delete a category."""
    category = await get_category_by_id(db, category_id)

    if category.children:
        raise ConflictError("Cannot delete category with children")

    await db.delete(category)
    await db.flush()


async def get_category_tree(db: AsyncSession) -> list[Category]:
    """Get all categories as a flat list (for tree building in templates)."""
    result = await db.execute(
        select(Category).options(selectinload(Category.children)).order_by(Category.name)
    )
    return list(result.scalars().all())


async def build_tree(categories: list[Category]) -> list[dict]:
    """Build a tree structure from a flat list of categories."""
    lookup: dict[uuid.UUID, dict] = {}
    roots: list[dict] = []

    for cat in categories:
        lookup[cat.id] = {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "children": [],
        }

    for cat in categories:
        node = lookup[cat.id]
        if cat.parent_category_id and cat.parent_category_id in lookup:
            lookup[cat.parent_category_id]["children"].append(node)
        else:
            roots.append(node)

    return roots
