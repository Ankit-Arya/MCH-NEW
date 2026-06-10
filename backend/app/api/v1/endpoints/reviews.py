from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import apply_review_scope
from app.models.all_models import (
    Inspection,
    InspectionAttributeScore,
    InspectionEntry,
    InspectionMedia,
    InspectionStatus,
    User,
)
from app.schemas.review import ReviewIn, ReviewOut
from app.services.review_service import review_by_line_manager, review_by_dgm, review_by_gm

router = APIRouter()


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
