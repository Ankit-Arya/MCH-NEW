from datetime import date, datetime
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import apply_inspection_scope, require_inspection_access, require_station_access
from app.models.all_models import (
    Contract,
    ContractStation,
    GradingOption,
    Inspection,
    InspectionAttribute,
    InspectionEntry,
    InspectionMedia,
    InspectionReview,
    InspectionStatus,
    InspectionSubArea,
    InspectionType,
    MediaType,
    RoleCode,
    Station,
    User,
    UserStationAccess,
)
from app.schemas.inspection import (
    InspectionDraftIn,
    InspectionEntryCreate,
    InspectionEntryOut,
    InspectionEntrySubmitIn,
    InspectionOut,
    InspectionStartIn,
    MediaOut,
)
from app.services.inspection_service import (
    create_inspection,
    entry_to_dict,
    list_entries,
    save_draft,
    save_entry,
    soft_delete_entry,
    submit_entry_based_inspection,
    submit_inspection,
)
from app.services.media_service import build_object_path, sha256_bytes, upload_bytes
from app.services.audit_service import audit_log

router = APIRouter()

START_ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN}
ACTION_REQUIRED_STATUSES = {
    InspectionStatus.DRAFT,
    InspectionStatus.RETURNED_FOR_CLARIFICATION,
}


def _iso(value):
    return value.isoformat() if value else None


def _inspection_score(inspection: Inspection) -> float:
    active_entries = [e for e in getattr(inspection, "entries", []) if not e.is_deleted]
    if active_entries:
        return round(sum(e.grade_percentage for e in active_entries) / len(active_entries), 2)
    if inspection.attribute_scores:
        return round(sum(s.grade_percentage for s in inspection.attribute_scores) / len(inspection.attribute_scores), 2)
    return 0.0


def _row(i: Inspection) -> dict:
    active_entries = [e for e in getattr(i, "entries", []) if not e.is_deleted]
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
        "entry_count": len(active_entries),
        "media_count": len([m for m in (i.media or []) if not m.is_deleted]),
    }


def _latest_review_payload(db: Session, inspection_id: int) -> dict | None:
    review = (
        db.query(InspectionReview)
        .filter(InspectionReview.inspection_id == inspection_id)
        .order_by(InspectionReview.reviewed_at.desc(), InspectionReview.id.desc())
        .first()
    )
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
    }


def _action_required_row(db: Session, inspection: Inspection) -> dict:
    row = _row(inspection)
    latest_review = _latest_review_payload(db, inspection.id)
    if inspection.status == InspectionStatus.RETURNED_FOR_CLARIFICATION:
        reason = "Returned by reviewer. Correct the inspection and resubmit."
        priority = 1
    else:
        reason = "Draft saved. Complete mandatory evidence and submit."
        priority = 2
    row.update(
        {
            "reason": reason,
            "priority": priority,
            "can_continue": inspection.status in ACTION_REQUIRED_STATUSES,
            "latest_review": latest_review,
            "latest_remarks": latest_review.get("comments") if latest_review else inspection.remarks,
            "latest_actor": latest_review.get("reviewer_name") if latest_review else None,
            "latest_actor_role": latest_review.get("reviewer_role") if latest_review else None,
            "latest_action_at": latest_review.get("reviewed_at") if latest_review else None,
        }
    )
    return row


def _validate_upload_file(media_type: MediaType, file: UploadFile, data: bytes) -> None:
    max_mb = settings.MAX_PHOTO_MB if media_type == MediaType.PHOTO else settings.MAX_VIDEO_MB
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max {max_mb} MB")
    if media_type == MediaType.PHOTO and file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="PHOTO upload must be an image file")
    if media_type == MediaType.VIDEO and file.content_type and not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="VIDEO upload must be a video file")


def _is_start_admin(user: User) -> bool:
    return bool(user.role and user.role.code in START_ADMIN_ROLES)


def _inspection_type_for_user(user: User) -> InspectionType:
    code = user.role.code if user and user.role else None
    if code == RoleCode.STATION_MANAGER:
        return InspectionType.SM_INSPECTION
    if code == RoleCode.EIT_MEMBER:
        return InspectionType.EIT_INSPECTION
    return InspectionType.SPECIAL_INSPECTION


def _explicit_user_station_ids(db: Session, user: User) -> set[int]:
    """Return only stations explicitly mapped to the logged-in user.

    Do not expand UserLineAccess here. For Start Inspection, line access must not
    become permission to start inspection at every station on that line.
    """

    return {
        row.station_id
        for row in db.query(UserStationAccess.station_id)
        .filter(
            UserStationAccess.user_id == user.id,
            UserStationAccess.is_active.is_(True),
        )
        .all()
    }


def _station_contract_status(db: Session, station: Station) -> dict:
    mappings = (
        db.query(ContractStation)
        .join(Contract, Contract.id == ContractStation.contract_id)
        .filter(
            ContractStation.station_id == station.id,
            ContractStation.is_active.is_(True),
            Contract.is_active.is_(True),
        )
        .all()
    )

    base = {
        "id": station.id,
        "station_id": station.id,
        "station_code": station.station_code,
        "station_name": station.station_name,
        "line_id": station.line_id,
        "contract_id": None,
        "contract_code": None,
        "contract_name": None,
        "is_startable": False,
        "message": None,
    }

    if not mappings:
        base["message"] = "Station is mapped to you but has no active contract mapping."
        return base

    if len(mappings) > 1:
        base["message"] = "Station has multiple active contract mappings. Keep only one active contract for Start Inspection."
        return base

    contract = mappings[0].contract
    base.update(
        {
            "contract_id": contract.id,
            "contract_code": contract.contract_code,
            "contract_name": contract.contract_name,
            "is_startable": True,
        }
    )
    return base


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
    query = apply_inspection_scope(
        db.query(Inspection).order_by(Inspection.inspection_date.desc(), Inspection.id.desc()),
        db,
        user,
    )
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


@router.get("/action-required")
def action_required_inspections(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the logged-in user's unfinished work separately from normal reports.

    Draft inspections and returned-for-clarification inspections are work items for the
    original submitter. They should not be hidden among completed report history.
    """

    query = (
        db.query(Inspection)
        .filter(
            Inspection.submitted_by == user.id,
            Inspection.status.in_([InspectionStatus.DRAFT, InspectionStatus.RETURNED_FOR_CLARIFICATION]),
        )
        .order_by(Inspection.updated_at.desc(), Inspection.id.desc())
    )
    total = query.count()
    pages = max(1, (total + size - 1) // size) if total else 1
    page = min(max(page, 1), pages)
    items = query.offset((page - 1) * size).limit(size).all()
    return {
        "items": [_action_required_row(db, item) for item in items],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
        "from_record": ((page - 1) * size + 1) if total else 0,
        "to_record": min(page * size, total),
        "counts": {
            "draft": query.filter(Inspection.status == InspectionStatus.DRAFT).count(),
            "returned": query.filter(Inspection.status == InspectionStatus.RETURNED_FOR_CLARIFICATION).count(),
        },
    }


@router.get("/start-options")
def start_options(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Options for Start Inspection.

    This endpoint is intentionally stricter than /master/bootstrap:
    - Non-admin users see only stations explicitly mapped to their own user.
    - UserLineAccess is NOT expanded here.
    - Contract is returned as a derived read-only value from station mapping.
    - Inspection type is returned as a derived read-only value from user role.
    """

    query = db.query(Station).filter(Station.is_active.is_(True)).order_by(Station.station_name)

    if not _is_start_admin(user):
        station_ids = _explicit_user_station_ids(db, user)
        if not station_ids:
            return {
                "current_role": user.role.code.value if user.role else None,
                "inspection_type": _inspection_type_for_user(user).value,
                "stations": [],
                "message": "No stations are directly mapped to this user.",
            }
        query = query.filter(Station.id.in_(station_ids))

    stations = [_station_contract_status(db, station) for station in query.all()]
    return {
        "current_role": user.role.code.value if user.role else None,
        "inspection_type": _inspection_type_for_user(user).value,
        "stations": stations,
    }


@router.get("/checklist")
def checklist(contract_id: int, station_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_station_access(db, user, station_id)
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    grading = db.query(GradingOption).filter_by(scheme_id=contract.grading_scheme_id).order_by(GradingOption.sort_order).all()
    attributes = db.query(InspectionAttribute).filter_by(is_active=True).order_by(InspectionAttribute.sort_order).all()
    sub_areas = db.query(InspectionSubArea).filter_by(is_active=True).order_by(InspectionSubArea.sort_order).all()
    return {
        "contract": contract,
        "station": db.get(Station, station_id),
        "grading_options": grading,
        "grades": grading,
        "attributes": attributes,
        "sub_areas": sub_areas,
    }


@router.post("/start", response_model=InspectionOut)
def start_inspection(payload: InspectionStartIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_inspection(db, payload, user)


@router.get("/{inspection_id}", response_model=InspectionOut)
def get_inspection(inspection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    require_inspection_access(db, user, inspection)
    return inspection


@router.put("/{inspection_id}/draft", response_model=InspectionOut)
def save_inspection_draft(inspection_id: int, payload: InspectionDraftIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return save_draft(db, inspection, payload, user)


@router.post("/{inspection_id}/entries", response_model=InspectionEntryOut)
def create_entry(inspection_id: int, payload: InspectionEntryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    entry = save_entry(db, inspection, payload, user)
    return entry_to_dict(db, entry)


@router.get("/{inspection_id}/entries", response_model=list[InspectionEntryOut])
def get_entries(inspection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    require_inspection_access(db, user, inspection)
    return list_entries(db, inspection.id)


@router.delete("/{inspection_id}/entries/{entry_id}")
def delete_entry(inspection_id: int, entry_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    soft_delete_entry(db, inspection, entry_id, user)
    return {"message": "Entry deleted"}


@router.post("/{inspection_id}/entries/{entry_id}/media", response_model=MediaOut)
async def upload_entry_media(
    inspection_id: int,
    entry_id: int,
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
    entry = db.get(InspectionEntry, entry_id)
    if not entry or entry.inspection_id != inspection.id or entry.is_deleted:
        raise HTTPException(status_code=404, detail="Entry not found")

    data = await file.read()
    _validate_upload_file(media_type, file, data)
    checksum = sha256_bytes(data)
    object_path = build_object_path(inspection.contract_id, inspection.station_id, inspection.id, f"entry-{entry.id}-{file.filename or 'upload.bin'}")
    upload_bytes(object_path, data, file.content_type)
    row = InspectionMedia(
        inspection_id=inspection.id,
        inspection_entry_id=entry.id,
        attribute_id=entry.attribute_id,
        sub_area_id=entry.sub_area_id,
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
    audit_log(db, actor=user, action="ENTRY_MEDIA_UPLOADED", entity_type="InspectionEntry", entity_id=entry.id, new_value={"object_path": object_path, "media_type": media_type.value})
    db.commit()
    db.refresh(row)
    return row


@router.post("/{inspection_id}/submit", response_model=InspectionOut)
def submit(
    inspection_id: int,
    payload: InspectionEntrySubmitIn | InspectionDraftIn | None = Body(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    # New UI path: if the inspection has entry records, use entry-based validation.
    has_entries = db.query(InspectionEntry).filter(
        InspectionEntry.inspection_id == inspection.id,
        InspectionEntry.is_deleted == False,  # noqa: E712
    ).first() is not None
    if has_entries or payload is None or isinstance(payload, InspectionEntrySubmitIn):
        remarks = getattr(payload, "remarks", None) if payload else None
        return submit_entry_based_inspection(db, inspection, user, remarks)

    # Legacy compatibility path for old checklist payloads.
    return submit_inspection(db, inspection, payload, user)


@router.post("/{inspection_id}/media", response_model=MediaOut)
async def upload_media_legacy(
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
    _validate_upload_file(media_type, file, data)
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
