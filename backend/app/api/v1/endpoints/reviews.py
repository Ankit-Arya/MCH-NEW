from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import apply_review_scope, require_inspection_access
from app.models.all_models import (
    Inspection,
    InspectionAttributeScore,
    InspectionEntry,
    InspectionMedia,
    InspectionReview,
    InspectionStatus,
    User,
)
from app.schemas.review import ReviewIn, ReviewOut
from app.services.review_service import review_by_line_manager, review_by_dgm, review_by_gm

router = APIRouter()


class WorkflowTrackerRequest(BaseModel):
    inspection_ids: list[int] = Field(default_factory=list)


def _pending_query(db: Session, user: User):
    query = db.query(Inspection).order_by(Inspection.created_at.desc(), Inspection.id.desc())
    return apply_review_scope(query, db, user)


def _inspection_score(db: Session, inspection_id: int) -> float:
    entries = db.query(InspectionEntry).filter(
        InspectionEntry.inspection_id == inspection_id,
        InspectionEntry.is_deleted.is_(False),
    ).all()
    if entries:
        return round(sum(e.grade_percentage or 0 for e in entries) / len(entries), 2)

    scores = db.query(InspectionAttributeScore).filter(
        InspectionAttributeScore.inspection_id == inspection_id,
    ).all()
    if scores:
        return round(sum(s.grade_percentage or 0 for s in scores) / len(scores), 2)

    return 0.0


def _iso(value):
    return value.isoformat() if value else None


def _review_payload(review: InspectionReview | None) -> dict | None:
    if not review:
        return None
    return {
        "id": review.id,
        "review_level": review.review_level,
        "reviewer_id": review.reviewer_id,
        "reviewer_name": review.reviewer.name if review.reviewer else None,
        "reviewer_role": review.reviewer_role,
        "action": review.action.value if getattr(review.action, "value", None) else str(review.action or ""),
        "comments": review.comments,
        "reviewed_at": _iso(review.reviewed_at),
        "recommended_penalty_amount": review.recommended_penalty_amount,
        "final_penalty_amount": review.final_penalty_amount,
    }


def _latest_review(reviews: list[InspectionReview], level: str) -> InspectionReview | None:
    matching = [row for row in reviews if row.review_level == level]
    if not matching:
        return None
    return sorted(matching, key=lambda row: row.reviewed_at or row.created_at, reverse=True)[0]


def _stage(key: str, label: str, status: str, at=None, by: str | None = None, action: str | None = None, note: str | None = None) -> dict:
    return {
        "key": key,
        "label": label,
        "status": status,
        "at": _iso(at) if not isinstance(at, str) else at,
        "by": by,
        "action": action,
        "note": note,
    }


def _workflow_tracker(db: Session, inspection: Inspection) -> dict:
    reviews = (
        db.query(InspectionReview)
        .filter(InspectionReview.inspection_id == inspection.id)
        .order_by(InspectionReview.reviewed_at.asc(), InspectionReview.id.asc())
        .all()
    )
    lm_review = _latest_review(reviews, "LINE_MANAGER")
    dgm_review = _latest_review(reviews, "DGM")
    gm_review = _latest_review(reviews, "GM")

    current_status = inspection.status.value if inspection.status else None
    submitter_name = inspection.submitter.name if inspection.submitter else None

    stages = [
        _stage(
            "inspection_done",
            "Inspection done",
            "done" if inspection.inspection_date else "pending",
            inspection.inspection_date.isoformat() if inspection.inspection_date else None,
            submitter_name,
            note="Actual inspection date",
        ),
        _stage(
            "submitted",
            "Submitted to LM/AM",
            "done" if inspection.submitted_at else "pending",
            inspection.submitted_at,
            submitter_name,
            note="Submitted for hierarchy review" if inspection.submitted_at else "Not submitted yet",
        ),
        _stage(
            "line_manager",
            "LM/AM forwarding",
            "done" if lm_review else ("current" if current_status == InspectionStatus.UNDER_LINE_MANAGER_REVIEW.value else "pending"),
            lm_review.reviewed_at if lm_review else None,
            lm_review.reviewer.name if lm_review and lm_review.reviewer else None,
            lm_review.action.value if lm_review and getattr(lm_review.action, "value", None) else None,
            lm_review.comments if lm_review else "LM/AM can forward to DGM or return for clarification.",
        ),
        _stage(
            "dgm",
            "DGM forwarding",
            "done" if dgm_review else ("current" if current_status == InspectionStatus.LINE_MANAGER_RECOMMENDED.value else "pending"),
            dgm_review.reviewed_at if dgm_review else None,
            dgm_review.reviewer.name if dgm_review and dgm_review.reviewer else None,
            dgm_review.action.value if dgm_review and getattr(dgm_review.action, "value", None) else None,
            dgm_review.comments if dgm_review else "DGM can forward to GM/Ops or return for clarification.",
        ),
        _stage(
            "gm",
            "GM/Ops final decision",
            "done" if gm_review else ("current" if current_status == InspectionStatus.GM_REVIEW_REQUIRED.value else "pending"),
            gm_review.reviewed_at if gm_review else None,
            gm_review.reviewer.name if gm_review and gm_review.reviewer else None,
            gm_review.action.value if gm_review and getattr(gm_review.action, "value", None) else None,
            gm_review.comments if gm_review else "GM/Ops gives final approval or final rejection.",
        ),
    ]

    completed = [stage for stage in stages if stage["status"] == "done"]
    current = next((stage for stage in stages if stage["status"] == "current"), None)

    return {
        "inspection_id": inspection.id,
        "inspection_no": inspection.inspection_no,
        "current_status": current_status,
        "current_stage": current["label"] if current else None,
        "completed_count": len(completed),
        "total_count": len(stages),
        "stages": stages,
        "reviews": [_review_payload(review) for review in reviews],
    }


def _review_row(db: Session, i: Inspection) -> dict:
    entry_count = db.query(InspectionEntry).filter(
        InspectionEntry.inspection_id == i.id,
        InspectionEntry.is_deleted.is_(False),
    ).count()
    media_count = db.query(InspectionMedia).filter(
        InspectionMedia.inspection_id == i.id,
        InspectionMedia.is_deleted.is_(False),
    ).count()

    return {
        "id": i.id,
        "inspection_no": i.inspection_no,
        "inspection_date": i.inspection_date.isoformat() if i.inspection_date else None,
        "station_id": i.station_id,
        "station_name": i.station.station_name if i.station else None,
        "contract_id": i.contract_id,
        "contract_code": i.contract.contract_code if i.contract else None,
        "submitted_by": i.submitted_by,
        "submitted_by_name": i.submitter.name if i.submitter else None,
        "inspection_type": i.inspection_type.value if i.inspection_type else None,
        "status": i.status.value if i.status else None,
        "score": _inspection_score(db, i.id),
        "entry_count": entry_count,
        "media_count": media_count,
        "created_at": i.created_at.isoformat() if getattr(i, "created_at", None) else None,
        "submitted_at": i.submitted_at.isoformat() if i.submitted_at else None,
        "workflow_tracker": _workflow_tracker(db, i),
    }


@router.get("/pending")
def pending_reviews(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = _pending_query(db, user)
    total = query.count()
    pages = max(1, ceil(total / size)) if total else 1
    page = min(max(page, 1), pages)
    items = query.offset((page - 1) * size).limit(size).all()
    return {
        "items": [_review_row(db, i) for i in items],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
        "from_record": ((page - 1) * size + 1) if total else 0,
        "to_record": min(page * size, total),
    }


@router.post("/workflow-trackers")
def workflow_trackers(payload: WorkflowTrackerRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return approval tracker details for report/review rows visible to the logged-in user."""
    ids = list(dict.fromkeys([int(item) for item in payload.inspection_ids if item]))[:200]
    if not ids:
        return []

    inspections = db.query(Inspection).filter(Inspection.id.in_(ids)).all()
    trackers = []
    for inspection in inspections:
        require_inspection_access(db, user, inspection)
        trackers.append(_workflow_tracker(db, inspection))
    return trackers


@router.post("/{inspection_id}/line-manager", response_model=ReviewOut)
def line_manager_review(inspection_id: int, payload: ReviewIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return review_by_line_manager(db, inspection, payload, user)


@router.post("/{inspection_id}/dgm", response_model=ReviewOut)
def dgm_review(inspection_id: int, payload: ReviewIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return review_by_dgm(db, inspection, payload, user)


@router.post("/{inspection_id}/gm", response_model=ReviewOut)
def gm_review(inspection_id: int, payload: ReviewIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return review_by_gm(db, inspection, payload, user)
