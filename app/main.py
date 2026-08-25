from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.auth.middleware import get_session
from app.config import get_settings

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    settings = get_settings()
    level = logging.DEBUG if settings.is_development else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class UserContextMiddleware(BaseHTTPMiddleware):
    """Inject current user into request.state for template rendering.

    Loads the full User model from DB so templates can access role, email, display_name, etc.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        session = get_session(request)
        request.state.current_user = None
        if session is not None:
            from sqlalchemy import select

            from app.db.engine import _get_session_factory
            from app.users.models import User

            session_factory = _get_session_factory()
            async with session_factory() as db:
                result = await db.execute(
                    select(User).where(User.supabase_id == session.user.supabase_id)
                )
                user = result.scalar_one_or_none()
                if user is not None and user.is_active:
                    request.state.current_user = user
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    logger.info("Starting application (env=%s)", get_settings().app_env)
    yield
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Nesti",
        description="Nesti — Home Inventory Catalog",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
    )

    templates = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=True,
    )
    app.state.jinja_env = templates

    app.add_middleware(UserContextMiddleware)

    app.mount("/static", StaticFiles(directory="static"), name="static")

    _register_error_handlers(app)
    _register_routes(app)
    _register_routers(app)

    return app


def _register_error_handlers(app: FastAPI) -> None:
    def _is_html_request(request: Request) -> bool:
        accept = request.headers.get("accept", "")
        path = request.url.path
        html_paths = (
            "/dashboard", "/items", "/categories", "/tags",
            "/locations", "/access", "/admin", "/scan",
            "/search", "/profile",
        )
        return "text/html" in accept or path.startswith(html_paths)

    @app.exception_handler(404)
    async def not_found_handler(
        request: Request, exc: Exception
    ) -> HTMLResponse | JSONResponse:
        if _is_html_request(request):
            return HTMLResponse(
                content="<h1>404 Not Found</h1>", status_code=404
            )
        return JSONResponse(content={"detail": "Not Found"}, status_code=404)

    @app.exception_handler(401)
    async def unauthorized_handler(
        request: Request, exc: Exception
    ) -> RedirectResponse | JSONResponse:
        if _is_html_request(request):
            return RedirectResponse(url="/auth/login", status_code=303)
        return JSONResponse(
            content={"detail": "Authentication required"},
            status_code=401,
            headers={"WWW-Authenticate": "Cookie"},
        )

    @app.exception_handler(403)
    async def forbidden_handler(
        request: Request, exc: Exception
    ) -> HTMLResponse | JSONResponse:
        if _is_html_request(request):
            return HTMLResponse(
                content="<h1>403 Forbidden</h1>", status_code=403
            )
        return JSONResponse(
            content={"detail": "Forbidden"},
            status_code=403,
        )

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Internal server error")
        return JSONResponse(
            content={"detail": "Internal server error"},
            status_code=500,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> HTMLResponse | JSONResponse:
        if _is_html_request(request):
            return HTMLResponse(content="<h1>422 — Помилка валідації</h1>", status_code=422)
        return JSONResponse(
            content={"detail": exc.errors()},
            status_code=422,
        )


def _register_routes(app: FastAPI) -> None:
    @app.get("/health", response_class=JSONResponse)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> RedirectResponse:
        return RedirectResponse(url="/dashboard", status_code=303)


def _register_routers(app: FastAPI) -> None:
    from app.access.routes import router as access_router
    from app.admin.routes import router as admin_router
    from app.api.v1.categories import router as api_categories_router
    from app.api.v1.locations import router as api_locations_router
    from app.api.v1.tags import router as api_tags_router
    from app.auth.routes import router as auth_router
    from app.backup.routes import router as backup_router
    from app.categories.routes import router as categories_router
    from app.dashboard.routes import router as dashboard_router
    from app.items.routes import router as items_router
    from app.labels.routes import router as labels_router
    from app.locations.routes import router as locations_router
    from app.media.routes import router as media_router
    from app.movements.routes import router as movements_router
    from app.qr.routes import router as qr_router
    from app.relationships.routes import router as relationships_router
    from app.search.routes import router as search_router
    from app.tags.routes import router as tags_router
    from app.users.routes import profile_router as profile_router_import
    from app.users.routes import router as users_router

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(users_router)
    app.include_router(profile_router_import)
    app.include_router(backup_router)
    app.include_router(categories_router)
    app.include_router(dashboard_router)
    app.include_router(tags_router)
    app.include_router(locations_router)
    app.include_router(access_router)
    app.include_router(items_router)
    app.include_router(labels_router)
    app.include_router(media_router)
    app.include_router(movements_router)
    app.include_router(qr_router)
    app.include_router(relationships_router)
    app.include_router(search_router)

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(api_categories_router)
    api_v1.include_router(api_tags_router)
    api_v1.include_router(api_locations_router)
    app.include_router(api_v1)


app = create_app()
