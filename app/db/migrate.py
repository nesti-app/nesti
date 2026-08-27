from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)


def _alembic_config():
    """Build an Alembic Config pointing at this project's migrations."""
    from alembic.config import Config

    project_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", _migration_database_url())
    return cfg


def _migration_database_url() -> str:
    """Apply the same asyncpg/SSL normalization used by the app engine."""
    from app.db.engine import _async_database_url

    return _async_database_url(get_settings().database_url)


def _upgrade_in_thread() -> None:
    """Run Alembic migrations to head. Safe to call via asyncio.to_thread."""
    from alembic import command

    cfg = _alembic_config()
    command.upgrade(cfg, "head")


async def run_migrations() -> None:
    """Apply pending Alembic migrations at application startup.

    Fail-safe: any migration error is logged so it can be diagnosed, but the
    application still starts. A migration failure must never take down the
    whole deployment.
    """
    if not get_settings().database_url:
        logger.warning("No DATABASE_URL configured; skipping migrations")
        return
    try:
        logger.info("Running database migrations...")
        await asyncio.to_thread(_upgrade_in_thread)
        logger.info("Database migrations complete")
    except Exception:
        logger.exception("Database migrations failed; continuing startup")
