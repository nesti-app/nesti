from __future__ import annotations

from enum import StrEnum
from typing import Literal, cast

from pydantic import BaseModel, Field

from app.common.forms import parse_bool

DEFAULT_LABEL_TYPE: Literal["compact", "full"] = "full"
DEFAULT_ORIENTATION: Literal["horizontal", "vertical"] = "horizontal"
DEFAULT_SIZE = "30x15"
DEFAULT_CUSTOM_WIDTH = 30
DEFAULT_CUSTOM_HEIGHT = 15
DEFAULT_NAME_FONT_SIZE = 14
DEFAULT_CODE_FONT_SIZE = 10
DEFAULT_MAX_NAME_LINES = 4
DEFAULT_WRAP_BY_WORDS = True


class LabelSize(StrEnum):
    SMALL_12x30 = "12x30"
    MEDIUM_15x30 = "15x30"
    MEDIUM_15x40 = "15x40"
    LARGE_20x30 = "20x30"
    LARGE_20x50 = "20x50"
    CUSTOM = "custom"


LABEL_PRESETS: dict[str, tuple[int, int]] = {
    "12x30": (12, 30),
    "15x30": (15, 30),
    "15x40": (15, 40),
    "20x30": (20, 30),
    "20x50": (20, 50),
    "30x12": (30, 12),
    "30x15": (30, 15),
    "40x15": (40, 15),
    "30x20": (30, 20),
    "50x20": (50, 20),
}


def parse_label_size(size: str, custom_width: int, custom_height: int) -> tuple[int, int]:
    """Resolve a size key (or ``custom``) into physical millimetres."""
    if size == "custom":
        return max(1, custom_width), max(1, custom_height)
    return LABEL_PRESETS.get(size, (15, 30))


class LabelRequest(BaseModel):
    size: LabelSize = LabelSize.MEDIUM_15x30
    custom_width_mm: int | None = None
    custom_height_mm: int | None = None
    dpi: int = 203

    def get_dimensions_mm(self) -> tuple[int, int]:
        if self.size == LabelSize.CUSTOM:
            w = self.custom_width_mm or 20
            h = self.custom_height_mm or 50
            return max(1, w), max(1, h)
        return LABEL_PRESETS[self.size.value]


class LabelSettingsData(BaseModel):
    """Validated default label configuration used across the app."""

    label_type: Literal["compact", "full"] = DEFAULT_LABEL_TYPE
    orientation: Literal["horizontal", "vertical"] = DEFAULT_ORIENTATION
    size: str = DEFAULT_SIZE
    custom_width: int = Field(DEFAULT_CUSTOM_WIDTH, ge=1, le=200)
    custom_height: int = Field(DEFAULT_CUSTOM_HEIGHT, ge=1, le=200)
    name_font_size: int = Field(DEFAULT_NAME_FONT_SIZE, ge=6, le=48)
    code_font_size: int = Field(DEFAULT_CODE_FONT_SIZE, ge=6, le=48)
    max_name_lines: int = Field(DEFAULT_MAX_NAME_LINES, ge=1, le=10)
    wrap_by_words: bool = DEFAULT_WRAP_BY_WORDS

    @classmethod
    def from_form(cls, **raw: str | int | bool | None) -> LabelSettingsData:
        def _int(value: str | int | bool | None, fallback: int) -> int:
            try:
                return int(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return fallback

        size = str(raw.get("size") or DEFAULT_SIZE)
        if size != "custom" and size not in LABEL_PRESETS:
            size = DEFAULT_SIZE

        label_type = str(raw.get("label_type") or DEFAULT_LABEL_TYPE)
        if label_type not in ("compact", "full"):
            label_type = DEFAULT_LABEL_TYPE

        orientation = str(raw.get("orientation") or DEFAULT_ORIENTATION)
        if orientation not in ("horizontal", "vertical"):
            orientation = DEFAULT_ORIENTATION

        return cls(
            label_type=cast(Literal["compact", "full"], label_type),
            orientation=cast(Literal["horizontal", "vertical"], orientation),
            size=size,
            custom_width=_int(raw.get("custom_width"), DEFAULT_CUSTOM_WIDTH),
            custom_height=_int(raw.get("custom_height"), DEFAULT_CUSTOM_HEIGHT),
            name_font_size=_int(raw.get("name_font_size"), DEFAULT_NAME_FONT_SIZE),
            code_font_size=_int(raw.get("code_font_size"), DEFAULT_CODE_FONT_SIZE),
            max_name_lines=_int(raw.get("max_name_lines"), DEFAULT_MAX_NAME_LINES),
            wrap_by_words=parse_bool(raw.get("wrap_by_words")),
        )
