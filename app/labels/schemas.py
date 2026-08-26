from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


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
