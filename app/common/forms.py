from __future__ import annotations


def parse_bool(value: str | int | bool | None) -> bool:
    """Interpret HTML form/query values ("on", "1", "true") as a boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "on", "yes")
