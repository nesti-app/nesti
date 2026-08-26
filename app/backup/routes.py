from __future__ import annotations

import json
import zipfile
from io import BytesIO

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment
from sqlalchemy.ext.asyncio import AsyncSession

from app.backup.service import SCHEMA_VERSION, export_inventory
from app.db.engine import get_db
from app.dependencies import require_admin
from app.users.models import User

router = APIRouter(prefix="/admin/backup", tags=["backup"])


@router.get("", response_class=HTMLResponse)
async def backup_page(
    request: Request,
    current_user: User = Depends(require_admin),
) -> HTMLResponse:
    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("admin/backup.html")
    html = template.render(current_user=current_user)
    return HTMLResponse(content=html)


@router.get("/export")
async def backup_export(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    data = await export_inventory(db)
    from datetime import UTC, datetime

    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    filename = f"inventory-{date_str}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
async def backup_import(
    request: Request,
    current_user: User = Depends(require_admin),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    content = await file.read()

    try:
        with zipfile.ZipFile(BytesIO(content), "r") as zf:
            names = zf.namelist()

            if "manifest.json" not in names:
                return _error_page("Invalid archive: missing manifest.json")

            manifest = json.loads(zf.read("manifest.json"))
            if manifest.get("format") != "nesti-backup":
                return _error_page("Invalid archive format")

            expected = SCHEMA_VERSION
            actual = manifest.get("schema_version")
            if actual != expected:
                return _error_page(
                    f"Schema version mismatch: expected {expected}, got {actual}"
                )

            required = [
                "items.json",
                "categories.json",
                "tags.json",
                "locations.json",
                "item_attributes.json",
                "item_relationships.json",
                "item_movements.json",
                "item_images.json",
            ]
            missing = [n for n in required if n not in names]
            if missing:
                return _error_page(f"Missing files: {', '.join(missing)}")

            summary = {}
            for name in required:
                data = json.loads(zf.read(name))
                summary[name] = len(data)

    except zipfile.BadZipFile:
        return _error_page("Invalid ZIP file")

    jinja_env: Environment = request.app.state.jinja_env
    template = jinja_env.get_template("admin/import_preview.html")
    html = template.render(
        manifest=manifest,
        summary=summary,
        filename=file.filename,
        current_user=current_user,
    )
    return HTMLResponse(content=html)


def _error_page(message: str) -> HTMLResponse:
    return HTMLResponse(
        content=(f"<div class='rounded-md bg-red-50 p-4 text-sm text-red-700'>{message}</div>"),
        status_code=400,
    )
