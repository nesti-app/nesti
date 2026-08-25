from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.dashboard.service import (
    get_dashboard_stats,
    get_recent_items,
    get_recently_updated_items,
)
from app.db.engine import get_db
from app.dependencies import get_current_user
from app.users.models import User

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    stats = await get_dashboard_stats(db)
    recent_items = await get_recent_items(db)
    updated_items = await get_recently_updated_items(db)

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("dashboard/index.html")
    html = template.render(
        stats=stats,
        recent_items=recent_items,
        updated_items=updated_items,
        current_user=user,
    )
    return HTMLResponse(content=html)
