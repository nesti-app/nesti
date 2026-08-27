from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.service import list_categories
from app.db.engine import get_db
from app.dependencies import get_optional_user
from app.locations.service import list_locations
from app.search.service import SearchParams, search_items
from app.tags.service import list_tags
from app.users.models import User

router = APIRouter(tags=["search"])


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str | None = Query(None),
    category_id: str | None = Query(None),
    location_id: str | None = Query(None),
    tag_id: str | None = Query(None),
    sort: str = Query("name_asc"),
    page: int = Query(1, ge=1),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    cat_uuid = uuid.UUID(category_id) if category_id else None
    loc_uuid = uuid.UUID(location_id) if location_id else None
    tag_uuid = uuid.UUID(tag_id) if tag_id else None

    params = SearchParams(
        q=q,
        category_id=cat_uuid,
        location_id=loc_uuid,
        tag_id=tag_uuid,
        sort=sort,
        page=page,
    )

    access_filters = None
    items, total = await search_items(db, params, access_filters)

    categories, _ = await list_categories(db)
    locations, _ = await list_locations(db)
    tags, _ = await list_tags(db)

    per_page = params.per_page
    total_pages = max(1, (total + per_page - 1) // per_page)

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("search/results.html")
    html = template.render(
        items=items,
        total=total,
        page=page,
        total_pages=total_pages,
        q=q or "",
        categories=categories,
        locations=locations,
        tags=tags,
        selected_category=cat_uuid,
        selected_location=loc_uuid,
        selected_tag=tag_uuid,
        sort=sort,
        current_user=user,
    )
    return HTMLResponse(content=html)
