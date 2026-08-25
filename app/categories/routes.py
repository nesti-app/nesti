from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.schemas import CategoryCreate, CategoryUpdate
from app.categories.service import (
    build_tree,
    create_category,
    delete_category,
    get_category_by_id,
    list_categories,
    update_category,
)
from app.db.engine import get_db
from app.dependencies import require_admin
from app.users.models import User

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_class=HTMLResponse)
async def categories_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    categories, total = await list_categories(db)
    tree = await build_tree(categories)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("categories/list.html")
    html = template.render(
        categories=categories,
        tree=tree,
        total=total,
        current_user=request.state.current_user,
    )
    return HTMLResponse(content=html)


@router.get("/new", response_class=None)
async def category_create_form(
    request: Request,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    categories, _ = await list_categories(db)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("categories/form.html")
    html = template.render(category=None, categories=categories, current_user=user)
    return HTMLResponse(content=html)


@router.post("/new")
async def category_create_submit(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    description: str = Form(""),
    parent_category_id: uuid.UUID | None = Form(None),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = CategoryCreate(
        name=name,
        slug=slug,
        description=description or None,
        parent_category_id=parent_category_id,
    )
    await create_category(db, data)
    return RedirectResponse(url="/categories", status_code=303)


@router.get("/{category_id}", response_class=HTMLResponse)
async def category_detail(
    request: Request,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    category = await get_category_by_id(db, category_id)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("categories/detail.html")
    html = template.render(category=category, current_user=request.state.current_user)
    return HTMLResponse(content=html)


@router.get("/{category_id}/edit", response_class=None)
async def category_edit_form(
    request: Request,
    category_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    category = await get_category_by_id(db, category_id)
    categories, _ = await list_categories(db)
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("categories/form.html")
    html = template.render(category=category, categories=categories, current_user=user)
    return HTMLResponse(content=html)


@router.post("/{category_id}/edit")
async def category_edit_submit(
    category_id: uuid.UUID,
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    description: str = Form(""),
    parent_category_id: uuid.UUID | None = Form(None),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    data = CategoryUpdate(
        name=name,
        slug=slug,
        description=description or None,
        parent_category_id=parent_category_id,
    )
    await update_category(db, category_id, data)
    return RedirectResponse(url=f"/categories/{category_id}", status_code=303)


@router.post("/{category_id}/delete")
async def category_delete(
    category_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    await delete_category(db, category_id)
    return RedirectResponse(url="/categories", status_code=303)
