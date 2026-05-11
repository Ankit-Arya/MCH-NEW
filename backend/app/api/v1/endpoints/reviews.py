from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.all_models import Inspection, InspectionStatus, User
from app.schemas.review import ReviewIn, ReviewOut
from app.services.review_service import review_by_line_manager, review_by_dgm, review_by_gm

router = APIRouter()


@router.get("/pending")
def pending_reviews(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Inspection).filter(Inspection.status.in_([
        InspectionStatus.UNDER_LINE_MANAGER_REVIEW,
        InspectionStatus.LINE_MANAGER_RECOMMENDED,
        InspectionStatus.GM_REVIEW_REQUIRED,
    ])).order_by(Inspection.created_at.desc()).limit(200).all()


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
