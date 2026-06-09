from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.all_models import Inspection, InspectionStatus, User
from app.schemas.review import ReviewIn, ReviewOut
from app.services.review_service import review_by_line_manager, review_by_dgm, review_by_gm

router = APIRouter()


def _pending_query(db: Session):
    return db.query(Inspection).filter(Inspection.status.in_([
        InspectionStatus.UNDER_LINE_MANAGER_REVIEW,
        InspectionStatus.LINE_MANAGER_RECOMMENDED,
        InspectionStatus.GM_REVIEW_REQUIRED,
    ])).order_by(Inspection.created_at.desc(), Inspection.id.desc())


def _review_row(i: Inspection) -> dict:
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
    query = _pending_query(db)
    total = query.count()
    pages = max(1, ceil(total / size)) if total else 1
    page = min(max(page, 1), pages)
    items = query.offset((page - 1) * size).limit(size).all()
    return {
        "items": [_review_row(i) for i in items],
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
