#!/usr/bin/env python3
"""Generate favicon and icons from a source PNG image.

Usage:
    uv run scripts/generate-icons.py path/to/nesti.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def generate_icons(source_path: str) -> None:
    src = Image.open(source_path).convert("RGBA")
    icons_dir = Path("static/icons")
    icons_dir.mkdir(parents=True, exist_ok=True)

    sizes = {
        "favicon-16.png": 16,
        "favicon-32.png": 32,
        "icon-192.png": 192,
        "icon-512.png": 512,
    }

    for filename, size in sizes.items():
        img = src.copy()
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        out = icons_dir / filename
        img.save(out, "PNG")
        print(f"  {out} ({size}x{size})")

    favicon = icons_dir / "favicon.svg"
    svg = _generate_svg_favicon(src)
    favicon.write_text(svg)
    print(f"  {favicon}")

    apple = icons_dir / "apple-touch-icon.png"
    img = src.copy()
    img.thumbnail((180, 180), Image.Resampling.LANCZOS)
    img.save(apple, "PNG")
    print(f"  {apple}")

    print("\nDone! Update templates/base.html favicon link if needed.")


def _generate_svg_favicon(src: Image.Image) -> str:
    thumb = src.copy()
    thumb.thumbnail((64, 64), Image.Resampling.LANCZOS)
    thumb.save("/tmp/_favicon_preview.png", "PNG")

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">\n'
        '  <rect width="64" height="64" rx="12" fill="#4f46e5"/>\n'
        '  <text x="32" y="44" font-family="sans-serif" font-size="32"'
        ' font-weight="bold" fill="white" text-anchor="middle">N</text>\n'
        "</svg>"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/generate-icons.py <source.png>")
        sys.exit(1)
    generate_icons(sys.argv[1])
