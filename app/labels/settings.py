from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.labels.models import SINGLETON_ID, LabelSettings
from app.labels.schemas import LabelSettingsData

_DEFAULTS = LabelSettingsData()


async def get_label_settings(db: AsyncSession) -> LabelSettingsData:
    """Return persisted default label settings, or built-in defaults if unset."""
    row = await _get_row(db)
    if row is None:
        return _DEFAULTS.model_copy()
    return LabelSettingsData(
        label_type=row.label_type,
        orientation=row.orientation,
        size=row.size,
        custom_width=row.custom_width,
        custom_height=row.custom_height,
        name_font_size=row.name_font_size,
        code_font_size=row.code_font_size,
        max_name_lines=row.max_name_lines,
        wrap_by_words=row.wrap_by_words,
    )


async def save_label_settings(db: AsyncSession, data: LabelSettingsData) -> None:
    """Upsert the singleton default label settings row."""
    row = await _get_row(db)
    if row is None:
        row = LabelSettings(id=SINGLETON_ID)
        db.add(row)

    row.label_type = data.label_type
    row.orientation = data.orientation
    row.size = data.size
    row.custom_width = data.custom_width
    row.custom_height = data.custom_height
    row.name_font_size = data.name_font_size
    row.code_font_size = data.code_font_size
    row.max_name_lines = data.max_name_lines
    row.wrap_by_words = data.wrap_by_words
    await db.flush()


async def _get_row(db: AsyncSession) -> LabelSettings | None:
    stmt = select(LabelSettings).where(LabelSettings.id == SINGLETON_ID)
    return (await db.execute(stmt)).scalar_one_or_none()
