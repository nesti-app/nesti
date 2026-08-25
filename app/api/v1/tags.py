from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.tags.schemas import TagCreate, TagResponse, TagUpdate
from app.tags.service import (
    create_tag,
    delete_tag,
    get_tag_by_id,
    list_tags,
    update_tag,
)

router = APIRouter(prefix="/tags", tags=["api-tags"])


@router.get("", response_model=list[TagResponse])
async def api_list_tags(
    page: int = 1,
    per_page: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[TagResponse]:
    tags, _ = await list_tags(db, page=page, per_page=per_page)
    return [TagResponse.model_validate(t) for t in tags]


@router.post("", response_model=TagResponse, status_code=201)
async def api_create_tag(
    data: TagCreate,
    db: AsyncSession = Depends(get_db),
) -> TagResponse:
    tag = await create_tag(db, data)
    return TagResponse.model_validate(tag)


@router.get("/{tag_id}", response_model=TagResponse)
async def api_get_tag(
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TagResponse:
    tag = await get_tag_by_id(db, tag_id)
    return TagResponse.model_validate(tag)


@router.patch("/{tag_id}", response_model=TagResponse)
async def api_update_tag(
    tag_id: uuid.UUID,
    data: TagUpdate,
    db: AsyncSession = Depends(get_db),
) -> TagResponse:
    tag = await update_tag(db, tag_id, data)
    return TagResponse.model_validate(tag)


@router.delete("/{tag_id}", status_code=204)
async def api_delete_tag(
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_tag(db, tag_id)
