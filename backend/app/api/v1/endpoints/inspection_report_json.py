from datetime import datetime, timezone
import hashlib
import hmac
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_inspection_access
from app.models.all_models import (
    Inspection,
    InspectionAttributeScore,
    InspectionEntry,
    InspectionMedia,
    InspectionReview,
    InspectionStatus,
    MediaType,
    User,
)

router = APIRouter()

EVIDENCE_URL_TTL_SECONDS = 300


def _iso(value):
    return value.isoformat() if value else None


def _enum_value(value):
    return value.value if getattr(value, "value", None) else value


# def _inspection_score(
#     entries: list[InspectionEntry],
#     scores: list[InspectionAttributeScore],
# ) -> float:
#     if entries:
#         return round(
#             sum(entry.grade_percentage or 0 for entry in entries) / len(entries),
#             2,
#         )

#     if scores:
#         return round(
#             sum(score.grade_percentage or 0 for score in scores) / len(scores),
#             2,
#         )

#     return 0.0


def _evidence_token(media_id: int) -> str:
    expires_at = int(time.time()) + EVIDENCE_URL_TTL_SECONDS
    message = f"{media_id}:{expires_at}".encode("utf-8")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()

    return f"{expires_at}.{signature}"


def _public_base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host or request.headers.get("host")
    protocol = forwarded_proto or request.url.scheme

    if host and not host.startswith(("api", "mch_api")):
        return f"{protocol}://{host}".rstrip("/")

    configured_origin = (settings.FRONTEND_ORIGIN or "").strip().rstrip("/")
    if configured_origin:
        return configured_origin

    return str(request.base_url).rstrip("/")


def _evidence_url(request: Request, media_id: int) -> str:
    base_url = _public_base_url(request)
    api_prefix = settings.API_PREFIX.rstrip("/")
    token = _evidence_token(media_id)

    # Uses the existing signed evidence endpoint in reports.py.
    return (
        f"{base_url}{api_prefix}/reports/evidence/"
        f"{media_id}?token={token}"
    )


def _media_payload(request: Request, media: InspectionMedia) -> dict:
    media_type = _enum_value(media.media_type)
    url = _evidence_url(request, media.id)

    return {
        "id": media.id,
        "inspection_id": media.inspection_id,
        "inspection_entry_id": media.inspection_entry_id,
        "attribute_id": media.attribute_id,
        "attribute_name": (
            media.attribute.name if media.attribute else None
        ),
        "sub_area_id": media.sub_area_id,
        "sub_area_name": (
            media.sub_area.name if media.sub_area else None
        ),
        "media_type": media_type,
        "original_file_name": media.original_file_name,
        "mime_type": media.mime_type,
        "file_size": media.file_size,
        "checksum": media.checksum,
        "processing_status": media.processing_status,
        "captured_at": _iso(media.captured_at),
        "uploaded_at": _iso(media.uploaded_at),
        "uploaded_by": media.uploaded_by,
        "uploaded_by_name": (
            media.uploader.name if media.uploader else None
        ),
        "location": {
            "latitude": media.captured_latitude,
            "longitude": media.captured_longitude,
            "gps_accuracy": media.gps_accuracy,
        },
        "image_url": (
            url if media.media_type == MediaType.PHOTO else None
        ),
        "video_url": (
            url if media.media_type == MediaType.VIDEO else None
        ),
        "url_expires_in_seconds": EVIDENCE_URL_TTL_SECONDS,
    }


@router.get("/{inspection_id}")
def get_inspection_report_json(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inspection = db.get(Inspection, inspection_id)

    if not inspection:
        raise HTTPException(
            status_code=404,
            detail="Inspection not found",
        )

    require_inspection_access(db, user, inspection)

    if inspection.status == InspectionStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Draft inspection reports cannot be generated",
        )

    entries = (
        db.query(InspectionEntry)
        .filter(
            InspectionEntry.inspection_id == inspection.id,
            InspectionEntry.is_deleted.is_(False),
        )
        .order_by(InspectionEntry.id.asc())
        .all()
    )

    attribute_scores = (
        db.query(InspectionAttributeScore)
        .filter(
            InspectionAttributeScore.inspection_id == inspection.id,
        )
        .order_by(InspectionAttributeScore.id.asc())
        .all()
    )

    media_rows = (
        db.query(InspectionMedia)
        .filter(
            InspectionMedia.inspection_id == inspection.id,
            InspectionMedia.is_deleted.is_(False),
        )
        .order_by(InspectionMedia.id.asc())
        .all()
    )

    reviews = (
        db.query(InspectionReview)
        .filter(InspectionReview.inspection_id == inspection.id)
        .order_by(
            InspectionReview.reviewed_at.asc(),
            InspectionReview.id.asc(),
        )
        .all()
    )

    media_items = [
        _media_payload(request, media)
        for media in media_rows
    ]

    media_by_entry: dict[int, list[dict]] = {}
    for media in media_items:
        entry_id = media["inspection_entry_id"]
        if entry_id is not None:
            media_by_entry.setdefault(entry_id, []).append(media)

    entry_items = []
    for entry in entries:
        evidence = media_by_entry.get(entry.id, [])

        entry_items.append(
            {
                "id": entry.id,
                "entry_no": entry.entry_no,
                "attribute_id": entry.attribute_id,
                "attribute_name": (
                    entry.attribute.name if entry.attribute else None
                ),
                "sub_area_id": entry.sub_area_id,
                "sub_area_name": (
                    entry.sub_area.name if entry.sub_area else None
                ),
                "grade_code": entry.grade_code,
                "score": entry.grade_percentage,
                "remarks": entry.remarks,
                "captured_at": _iso(entry.captured_at),
                "created_by": entry.created_by,
                "created_by_name": (
                    entry.creator.name if entry.creator else None
                ),
                "location": {
                    "latitude": entry.captured_latitude,
                    "longitude": entry.captured_longitude,
                    "gps_accuracy": entry.gps_accuracy,
                },
                "photo_count": sum(
                    item["media_type"] == MediaType.PHOTO.value
                    for item in evidence
                ),
                "video_count": sum(
                    item["media_type"] == MediaType.VIDEO.value
                    for item in evidence
                ),
                "evidence": evidence,
            }
        )

    review_items = [
        {
            "id": review.id,
            "review_level": review.review_level,
            "reviewer_id": review.reviewer_id,
            "reviewer_name": (
                review.reviewer.name if review.reviewer else None
            ),
            "reviewer_role": review.reviewer_role,
            "action": _enum_value(review.action),
            "comments": review.comments,
            "recommended_penalty_amount": (
                review.recommended_penalty_amount
            ),
            "final_penalty_amount": review.final_penalty_amount,
            "reviewed_at": _iso(review.reviewed_at),
        }
        for review in reviews
    ]

    device_info = (
        inspection.device_info
        if isinstance(inspection.device_info, dict)
        else {}
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inspection": {
            "id": inspection.id,
            "inspection_no": inspection.inspection_no,
            "inspection_date": _iso(inspection.inspection_date),
            "inspection_type": _enum_value(
                inspection.inspection_type
            ),
            "status": _enum_value(inspection.status),
            "remarks": inspection.remarks,
            "started_at": _iso(inspection.started_at),
            "submitted_at": _iso(inspection.submitted_at),
            "submitted_by": inspection.submitted_by,
            "submitted_by_name": (
                inspection.submitter.name
                if inspection.submitter
                else None
            ),
            "station_id": inspection.station_id,
            "station_name": (
                inspection.station.station_name
                if inspection.station
                else None
            ),
            "contract_id": inspection.contract_id,
            "contract_code": (
                inspection.contract.contract_code
                if inspection.contract
                else None
            ),
            "location": {
                "latitude": inspection.latitude,
                "longitude": inspection.longitude,
                "gps_accuracy": inspection.gps_accuracy,
            },
            "is_late": inspection.is_late,
            "is_before_10am": inspection.is_before_10am,
        },
        "emergency": {
            "is_emergency": bool(
                device_info.get("emergency_inspection")
            ),
            "emergency_reason": (
                device_info.get("emergency_reason")
                or device_info.get("reason")
            ),
            "normal_station_assignment_bypassed": bool(
                device_info.get(
                    "normal_station_assignment_bypassed"
                )
            ),
        },
        "findings": {
            "entries": entry_items,
            "attribute_scores": [
                {
                    "id": score.id,
                    "attribute_id": score.attribute_id,
                    "attribute_name": (
                        score.attribute.name
                        if score.attribute
                        else None
                    ),
                    "grade_code": score.grade_code,
                    "score": score.grade_percentage,
                    "remarks": score.remarks,
                }
                for score in attribute_scores
            ],
        },
        "reviews": review_items,
        "evidence": {
            "total": len(media_items),
            "photo_count": sum(
                item["media_type"] == MediaType.PHOTO.value
                for item in media_items
            ),
            "video_count": sum(
                item["media_type"] == MediaType.VIDEO.value
                for item in media_items
            ),
            "items": media_items,
        },
    }