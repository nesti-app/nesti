from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.locations.schemas import LocationCreate, LocationResponse, LocationUpdate
from app.locations.service import (
    create_location,
    delete_location,
    get_location_by_id,
    list_locations,
    update_location,
)

router = APIRouter(prefix="/locations", tags=["api-locations"])


@router.get("", response_model=list[LocationResponse])
async def api_list_locations(
    page: int = 1,
    per_page: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[LocationResponse]:
    locations, _ = await list_locations(db, page=page, per_page=per_page)
    return [LocationResponse.model_validate(loc) for loc in locations]


@router.post("", response_model=LocationResponse, status_code=201)
async def api_create_location(
    data: LocationCreate,
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    location = await create_location(db, data)
    return LocationResponse.model_validate(location)


@router.get("/{location_id}", response_model=LocationResponse)
async def api_get_location(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    location = await get_location_by_id(db, location_id)
    return LocationResponse.model_validate(location)


@router.patch("/{location_id}", response_model=LocationResponse)
async def api_update_location(
    location_id: uuid.UUID,
    data: LocationUpdate,
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    location = await update_location(db, location_id, data)
    return LocationResponse.model_validate(location)


@router.delete("/{location_id}", status_code=204)
async def api_delete_location(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_location(db, location_id)
