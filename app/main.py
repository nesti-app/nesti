from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
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
    """Inject current user info into request.state for template rendering."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        session = get_session(request)
        request.state.current_user = session.user if session else None
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
        description="Home Inventory Management System",
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
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> HTMLResponse:
        return HTMLResponse(content="<h1>404 — Not Found</h1>", status_code=404)

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
    ) -> JSONResponse:
        return JSONResponse(
            content={"detail": exc.errors()},
            status_code=422,
        )


def _register_routes(app: FastAPI) -> None:
    @app.get("/health", response_class=JSONResponse)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        jinja_env: Environment = app.state.jinja_env
        template = jinja_env.get_template("index.html")
        html = template.render(current_user=getattr(request.state, "current_user", None))
        return HTMLResponse(content=html)


def _register_routers(app: FastAPI) -> None:
    from app.api.v1.categories import router as api_categories_router
    from app.api.v1.locations import router as api_locations_router
    from app.api.v1.tags import router as api_tags_router
    from app.auth.routes import router as auth_router
    from app.categories.routes import router as categories_router
    from app.locations.routes import router as locations_router
    from app.tags.routes import router as tags_router
    from app.users.routes import router as users_router

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(categories_router)
    app.include_router(tags_router)
    app.include_router(locations_router)

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(api_categories_router)
    api_v1.include_router(api_tags_router)
    api_v1.include_router(api_locations_router)
    app.include_router(api_v1)


app = create_app()
