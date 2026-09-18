from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.labels.schemas import (
    DEFAULT_CODE_FONT_SIZE,
    DEFAULT_CUSTOM_HEIGHT,
    DEFAULT_CUSTOM_WIDTH,
    DEFAULT_LABEL_TYPE,
    DEFAULT_MAX_NAME_LINES,
    DEFAULT_NAME_FONT_SIZE,
    DEFAULT_ORIENTATION,
    DEFAULT_SIZE,
    DEFAULT_WRAP_BY_WORDS,
)

SINGLETON_ID = "default"


class LabelSettings(TimestampMixin, Base):
    """Singleton row holding the application-wide default label configuration."""

    __tablename__ = "label_settings"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=SINGLETON_ID)
    label_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DEFAULT_LABEL_TYPE
    )
    orientation: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DEFAULT_ORIENTATION
    )
    size: Mapped[str] = mapped_column(String(16), nullable=False, default=DEFAULT_SIZE)
    custom_width: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_CUSTOM_WIDTH
    )
    custom_height: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_CUSTOM_HEIGHT
    )
    name_font_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_NAME_FONT_SIZE
    )
    code_font_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_CODE_FONT_SIZE
    )
    max_name_lines: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_MAX_NAME_LINES
    )
    wrap_by_words: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=DEFAULT_WRAP_BY_WORDS
    )

    def __repr__(self) -> str:
        return f"<LabelSettings {self.label_type}/{self.orientation}/{self.size}>"
