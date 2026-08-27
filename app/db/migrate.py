from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import get_settings

logger = logging.getLogger(__name__)


def _alembic_config() -> Config:
    """Build an Alembic Config pointing at this project's migrations."""
    project_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    return cfg


def _upgrade_in_thread() -> None:
    """Run Alembic migrations to head. Safe to call via asyncio.to_thread."""
    cfg = _alembic_config()
    try:
        command.upgrade(cfg, "head")
    except Exception:
        logger.exception("Database migration failed")
        raise


async def run_migrations() -> None:
    """Apply pending Alembic migrations at application startup."""
    if not get_settings().database_url:
        logger.warning("No DATABASE_URL configured; skipping migrations")
        return
    logger.info("Running database migrations...")
    await asyncio.to_thread(_upgrade_in_thread)
    logger.info("Database migrations complete")
