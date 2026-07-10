from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from minio.error import S3Error
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_inspection_access
from app.models.all_models import Inspection, InspectionMedia, User
from app.services.media_service import download_bytes

router = APIRouter()


def _inline_filename(filename: str | None, fallback: str = "evidence") -> str:
    safe = (filename or fallback).replace("\\", "_").replace("/", "_").replace('"', "")
    return safe or fallback


@router.get("/{media_id}/preview")
def preview_inspection_media(
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Authenticated inline preview for saved inspection evidence."""

    media = db.get(InspectionMedia, media_id)
    if not media or media.is_deleted:
        raise HTTPException(status_code=404, detail="Evidence file not found")

    inspection = db.get(Inspection, media.inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    require_inspection_access(db, user, inspection)

    try:
        data = download_bytes(media.object_path)
    except S3Error as exc:
        raise HTTPException(status_code=404, detail="Evidence file not found in storage") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load evidence preview") from exc

    filename = _inline_filename(media.original_file_name, f"evidence-{media.id}")
    return Response(
        content=data,
        media_type=media.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=60",
        },
    )
