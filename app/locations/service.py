from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.locations.models import Location
from app.locations.schemas import LocationCreate, LocationUpdate


async def list_locations(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 100,
) -> tuple[list[Location], int]:
    """List all locations with pagination."""
    count_result = await db.execute(select(func.count()).select_from(Location))
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Location).order_by(Location.name).offset(offset).limit(per_page)
    )
    return list(result.scalars().all()), total


async def get_location_by_id(db: AsyncSession, location_id: uuid.UUID) -> Location:
    """Get a location by ID."""
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()
    if location is None:
        raise NotFoundError("Location not found")
    return location


async def create_location(db: AsyncSession, data: LocationCreate) -> Location:
    """Create a new location."""
    if data.parent_location_id is not None:
        await get_location_by_id(db, data.parent_location_id)

    location = Location(
        name=data.name,
        description=data.description,
        parent_location_id=data.parent_location_id,
    )
    db.add(location)
    await db.flush()
    await db.refresh(location)
    return location


async def update_location(
    db: AsyncSession,
    location_id: uuid.UUID,
    data: LocationUpdate,
) -> Location:
    """Update a location."""
    location = await get_location_by_id(db, location_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    await db.flush()
    await db.refresh(location)
    return location


async def delete_location(db: AsyncSession, location_id: uuid.UUID) -> None:
    """Delete a location."""
    location = await get_location_by_id(db, location_id)

    if location.children:
        raise ConflictError("Cannot delete location with children")

    await db.delete(location)
    await db.flush()


async def build_tree(locations: list[Location]) -> list[dict]:
    """Build a tree structure from a flat list of locations."""
    lookup: dict[uuid.UUID, dict] = {}
    roots: list[dict] = []

    for loc in locations:
        lookup[loc.id] = {
            "id": loc.id,
            "name": loc.name,
            "children": [],
        }

    for loc in locations:
        node = lookup[loc.id]
        if loc.parent_location_id and loc.parent_location_id in lookup:
            lookup[loc.parent_location_id]["children"].append(node)
        else:
            roots.append(node)

    return roots
