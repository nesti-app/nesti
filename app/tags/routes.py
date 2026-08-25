from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.dependencies import require_admin
from app.tags.schemas import TagCreate, TagUpdate
from app.tags.service import (
    create_tag,
    delete_tag,
    get_tag_by_id,
    list_tags,
    search_tags,
    update_tag,
)
from app.users.models import User

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_class=HTMLResponse)
async def tags_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    tags, total = await list_tags(db)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("tags/list.html")
    html = template.render(tags=tags, total=total)
    return HTMLResponse(content=html)


@router.get("/new", response_class=None)
async def tag_create_form(
    request: Request,
    user: User = Depends(require_admin),
) -> Response:
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("tags/form.html")
    html = template.render(tag=None)
    return HTMLResponse(content=html)


@router.post("/new")
async def tag_create_submit(
    name: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = TagCreate(name=name)
    await create_tag(db, data)
    return RedirectResponse(url="/tags", status_code=303)


@router.get("/{tag_id}", response_class=HTMLResponse)
async def tag_detail(
    request: Request,
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    tag = await get_tag_by_id(db, tag_id)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("tags/detail.html")
    html = template.render(tag=tag)
    return HTMLResponse(content=html)


@router.get("/{tag_id}/edit", response_class=None)
async def tag_edit_form(
    request: Request,
    tag_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    tag = await get_tag_by_id(db, tag_id)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("tags/form.html")
    html = template.render(tag=tag)
    return HTMLResponse(content=html)


@router.post("/{tag_id}/edit")
async def tag_edit_submit(
    tag_id: uuid.UUID,
    name: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = TagUpdate(name=name)
    await update_tag(db, tag_id, data)
    return RedirectResponse(url=f"/tags/{tag_id}", status_code=303)


@router.post("/{tag_id}/delete")
async def tag_delete(
    tag_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await delete_tag(db, tag_id)
    return RedirectResponse(url="/tags", status_code=303)


@router.get("/search/json")
async def tags_search(
    q: str = "",
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    tags = await search_tags(db, q)
    return [{"id": str(t.id), "name": t.name} for t in tags]
