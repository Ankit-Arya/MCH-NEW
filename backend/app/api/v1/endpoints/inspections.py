
from datetime import date, datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_station_access
from app.models.all_models import (
    Contract,
    GradingOption,
    Inspection,
    InspectionAttribute,
    InspectionMedia,
    InspectionStatus,
    InspectionSubArea,
    InspectionType,
    MediaType,
    Station,
    User,
)
from app.schemas.inspection import InspectionStartIn, InspectionDraftIn, InspectionOut, MediaOut
from app.services.inspection_service import create_inspection, submit_inspection
from app.services.media_service import build_object_path, sha256_bytes, upload_bytes
from app.services.audit_service import audit_log

router = APIRouter()


def _inspection_score(inspection: Inspection) -> float:
    if not inspection.attribute_scores:
        return 0.0
    return round(sum(s.grade_percentage for s in inspection.attribute_scores) / len(inspection.attribute_scores), 2)


def _row(i: Inspection) -> dict:
    return {
        "id": i.id,
        "inspection_no": i.inspection_no,
        "inspection_date": i.inspection_date.isoformat() if i.inspection_date else None,
        "inspection_type": i.inspection_type.value,
        "status": i.status.value,
        "station_id": i.station_id,
        "station_name": i.station.station_name if i.station else None,
        "contract_id": i.contract_id,
        "contract_code": i.contract.contract_code if i.contract else None,
        "submitted_by": i.submitted_by,
        "submitted_by_name": i.submitter.name if i.submitter else None,
        "score": _inspection_score(i),
        "submitted_at": i.submitted_at.isoformat() if i.submitted_at else None,
        "is_late": i.is_late,
        "media_count": len(i.media or []),
    }


@router.get("")
def list_inspections(
    from_date: date | None = None,
    to_date: date | None = None,
    station_id: int | None = None,
    contract_id: int | None = None,
    submitted_by: int | None = None,
    inspection_type: InspectionType | None = None,
    status: InspectionStatus | None = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Inspection).order_by(Inspection.inspection_date.desc(), Inspection.id.desc())
    if from_date:
        query = query.filter(Inspection.inspection_date >= from_date)
    if to_date:
        query = query.filter(Inspection.inspection_date <= to_date)
    if station_id:
        query = query.filter(Inspection.station_id == station_id)
    if contract_id:
        query = query.filter(Inspection.contract_id == contract_id)
    if submitted_by:
        query = query.filter(Inspection.submitted_by == submitted_by)
    if inspection_type:
        query = query.filter(Inspection.inspection_type == inspection_type)
    if status:
        query = query.filter(Inspection.status == status)
    return [_row(i) for i in query.limit(limit).all()]


@router.get("/checklist")
def checklist(
    contract_id: int,
    station_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    require_station_access(db, user, station_id)

    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    station = db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    grading = (
        db.query(GradingOption)
        .filter_by(scheme_id=contract.grading_scheme_id)
        .order_by(GradingOption.sort_order)
        .all()
    )

    attributes = (
        db.query(InspectionAttribute)
        .filter_by(is_active=True)
        .order_by(InspectionAttribute.sort_order)
        .all()
    )

    sub_areas = (
        db.query(InspectionSubArea)
        .filter_by(is_active=True)
        .order_by(InspectionSubArea.sort_order)
        .all()
    )

    return {
        "contract": {
            "id": contract.id,
            "contract_code": contract.contract_code,
            "grading_scheme_id": contract.grading_scheme_id,
        },

        "station": {
            "id": station.id,
            "station_name": station.station_name,
        },

        "grading_options": [
            {
                "id": g.id,
                "scheme_id": g.scheme_id,
                "grade_code": g.grade_code,

                # use whichever field exists in your model
                "grade_label": getattr(g, "grade_label", None)
                    or getattr(g, "label", None)
                    or getattr(g, "name", None)
                    or g.grade_code,

                # IMPORTANT FIX
                # your model does not have g.grade_percentage
                "grade_percentage": getattr(g, "percentage", None)
                    or getattr(g, "score_percentage", None)
                    or getattr(g, "marks_percentage", None)
                    or 0,

                "sort_order": g.sort_order,
            }
            for g in grading
        ],

        "attributes": [
            {
                "id": a.id,
                "attribute_name": getattr(a, "attribute_name", None)
                    or getattr(a, "name", None)
                    or f"Attribute {a.id}",
                "sort_order": a.sort_order,
                "is_active": a.is_active,
            }
            for a in attributes
        ],

        "sub_areas": [
            {
                "id": s.id,
                "sub_area_name": getattr(s, "sub_area_name", None)
                    or getattr(s, "name", None)
                    or f"Sub Area {s.id}",
                "sort_order": s.sort_order,
                "is_active": s.is_active,
            }
            for s in sub_areas
        ],
    }


@router.post("/start", response_model=InspectionOut)
def start_inspection(payload: InspectionStartIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_inspection(db, payload, user)


@router.get("/{inspection_id}", response_model=InspectionOut)
def get_inspection(inspection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    require_station_access(db, user, inspection.station_id)
    return inspection


@router.put("/{inspection_id}/draft", response_model=InspectionOut)
def save_inspection_draft(inspection_id: int, payload: InspectionDraftIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    from app.services.inspection_service import save_draft
    return save_draft(db, inspection, payload, user)


@router.post("/{inspection_id}/submit", response_model=InspectionOut)
def submit(inspection_id: int, payload: InspectionDraftIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return submit_inspection(db, inspection, payload, user)


@router.post("/{inspection_id}/media", response_model=MediaOut)
async def upload_media(
    inspection_id: int,
    attribute_id: int = Form(...),
    sub_area_id: int = Form(...),
    media_type: MediaType = Form(...),
    captured_latitude: float | None = Form(None),
    captured_longitude: float | None = Form(None),
    gps_accuracy: float | None = Form(None),
    captured_at: datetime | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if inspection.status not in [InspectionStatus.DRAFT, InspectionStatus.RETURNED_FOR_CLARIFICATION]:
        raise HTTPException(status_code=400, detail="Cannot upload media after submission")
    require_station_access(db, user, inspection.station_id)

    data = await file.read()
    max_mb = settings.MAX_PHOTO_MB if media_type == MediaType.PHOTO else settings.MAX_VIDEO_MB
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max {max_mb} MB")
    checksum = sha256_bytes(data)
    object_path = build_object_path(inspection.contract_id, inspection.station_id, inspection.id, file.filename or "upload.bin")
    upload_bytes(object_path, data, file.content_type)
    row = InspectionMedia(
        inspection_id=inspection.id,
        attribute_id=attribute_id,
        sub_area_id=sub_area_id,
        media_type=media_type,
        object_path=object_path,
        original_file_name=file.filename or "upload.bin",
        mime_type=file.content_type,
        file_size=len(data),
        checksum=checksum,
        captured_latitude=captured_latitude,
        captured_longitude=captured_longitude,
        gps_accuracy=gps_accuracy,
        captured_at=captured_at,
        uploaded_by=user.id,
        processing_status="UPLOADED",
    )
    db.add(row)
    audit_log(db, actor=user, action="MEDIA_UPLOADED", entity_type="Inspection", entity_id=inspection.id, new_value={"object_path": object_path})
    db.commit()
    db.refresh(row)
    return row
