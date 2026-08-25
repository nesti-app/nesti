from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment
from starlette.responses import Response

from app.auth.middleware import clear_session, get_session, set_session
from app.auth.service import auth_service
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_class=None)
async def login_page(request: Request) -> Response:
    """Show login page or redirect to Supabase OAuth."""
    session = get_session(request)
    if session is not None:
        return RedirectResponse(url="/", status_code=303)

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("auth/login.html")
    html = template.render()
    return HTMLResponse(content=html)


@router.get("/login/supabase")
async def login_supabase(request: Request) -> RedirectResponse:
    """Redirect to Supabase hosted login page."""
    settings = get_settings()
    redirect_to = f"{settings.app_url}/auth/callback"
    login_url = await auth_service.get_supabase_login_url(redirect_to=redirect_to)
    return RedirectResponse(url=login_url, status_code=303)


@router.get("/callback")
async def auth_callback(request: Request) -> RedirectResponse:
    """Handle OAuth callback from Supabase."""
    code = request.query_params.get("code")
    if not code:
        return RedirectResponse(url="/auth/login?error=no_code", status_code=303)

    tokens = await auth_service.exchange_code_for_session(code)
    if tokens is None:
        return RedirectResponse(url="/auth/login?error=token_exchange_failed", status_code=303)

    response = RedirectResponse(url="/", status_code=303)
    set_session(response, tokens["access_token"], tokens["refresh_token"])
    return response


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Log out the current user."""
    session = get_session(request)
    if session is not None:
        await auth_service.sign_out(session.access_token)

    response = RedirectResponse(url="/auth/login", status_code=303)
    clear_session(response)
    return response
