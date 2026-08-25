from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.schemas import CategoryCreate, CategoryResponse, CategoryUpdate
from app.categories.service import (
    create_category,
    delete_category,
    get_category_by_id,
    list_categories,
    update_category,
)
from app.db.engine import get_db

router = APIRouter(prefix="/categories", tags=["api-categories"])


@router.get("", response_model=list[CategoryResponse])
async def api_list_categories(
    page: int = 1,
    per_page: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[CategoryResponse]:
    categories, _ = await list_categories(db, page=page, per_page=per_page)
    return [CategoryResponse.model_validate(c) for c in categories]


@router.post("", response_model=CategoryResponse, status_code=201)
async def api_create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    category = await create_category(db, data)
    return CategoryResponse.model_validate(category)


@router.get("/{category_id}", response_model=CategoryResponse)
async def api_get_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    category = await get_category_by_id(db, category_id)
    return CategoryResponse.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def api_update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    category = await update_category(db, category_id, data)
    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}", status_code=204)
async def api_delete_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_category(db, category_id)
