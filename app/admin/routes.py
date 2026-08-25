from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment

from app.dependencies import require_admin
from app.users.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("", response_class=HTMLResponse)
async def admin_index(
    request: Request,
    current_user: User = Depends(require_admin),
) -> HTMLResponse:
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("admin/index.html")
    html = template.render(current_user=current_user)
    return HTMLResponse(content=html)
