from datetime import date, datetime, timedelta
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
from app.services.media_service import EvidenceProcessingError, build_object_path, prepare_evidence_media, sha256_bytes, upload_bytes
from app.services.audit_service import audit_log
from app.models.kpi_chemical import InspectionKpiContext, KPI_6_CLEANLINESS, KPI_CHEMICALS

router = APIRouter()

START_ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN}
ACTION_REQUIRED_STATUSES = {
    InspectionStatus.DRAFT,
    InspectionStatus.RETURNED_FOR_CLARIFICATION,
}
ALLOWED_KPI_CATEGORIES = {KPI_6_CLEANLINESS, KPI_CHEMICALS}
SUBMITTED_WEEKLY_STATUSES = {
    InspectionStatus.UNDER_LINE_MANAGER_REVIEW,
    InspectionStatus.LINE_MANAGER_RECOMMENDED,
    InspectionStatus.DGM_APPROVED,
    InspectionStatus.DGM_REJECTED,
    InspectionStatus.GM_REVIEW_REQUIRED,
    InspectionStatus.GM_REVIEWED,
    InspectionStatus.CLOSED,
}
WEEKLY_INSPECTION_TARGETS = {
    RoleCode.STATION_MANAGER: {
        "required": 3,
        "label": "Station Manager weekly inspection target",
        "role_label": "SM",
    },
    RoleCode.EIT_MEMBER: {
        "required": 1,
        "label": "EIT weekly inspection target",
        "role_label": "EIT",
    },
}


def _kpi_category_for(db: Session, inspection_id: int) -> str:
    ctx = db.query(InspectionKpiContext).filter_by(inspection_id=inspection_id).first()
    return ctx.kpi_category if ctx else KPI_6_CLEANLINESS


def _attach_kpi_category(db: Session, inspection: Inspection) -> Inspection:
    setattr(inspection, "kpi_category", _kpi_category_for(db, inspection.id))
    return inspection


def _set_kpi_category(db: Session, inspection: Inspection, kpi_category: str | None) -> None:
    category = (kpi_category or KPI_6_CLEANLINESS).strip()
    if category not in ALLOWED_KPI_CATEGORIES:
        raise HTTPException(status_code=422, detail="Unsupported KPI category")
    ctx = db.query(InspectionKpiContext).filter_by(inspection_id=inspection.id).first()
    if not ctx:
        ctx = InspectionKpiContext(inspection_id=inspection.id, kpi_category=category)
        db.add(ctx)
    else:
        ctx.kpi_category = category
    db.flush()


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
        "kpi_category": getattr(i, "kpi_category", KPI_6_CLEANLINESS),
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


def _current_week_window(today: date | None = None) -> tuple[date, date]:
    """Return Monday-Sunday date range for weekly inspection target checks."""

    current = today or date.today()
    week_start = current - timedelta(days=current.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def _weekly_target_summary(db: Session, user: User) -> dict:
    role_code = user.role.code if user and user.role else None
    target = WEEKLY_INSPECTION_TARGETS.get(role_code)
    week_start, week_end = _current_week_window()

    if not target:
        return {
            "applies": False,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "required": 0,
            "completed": 0,
            "remaining": 0,
            "is_complete": True,
            "role_label": user.role.code.value if user.role else None,
            "message": "No weekly self-inspection target is configured for this role.",
        }

    required = int(target["required"])
    completed = (
        db.query(Inspection)
        .filter(
            Inspection.submitted_by == user.id,
            Inspection.inspection_date >= week_start,
            Inspection.inspection_date <= week_end,
            Inspection.status.in_(SUBMITTED_WEEKLY_STATUSES),
        )
        .count()
    )
    remaining = max(0, required - completed)
    is_complete = completed >= required
    role_label = str(target["role_label"])

    return {
        "applies": True,
        "label": target["label"],
        "role_label": role_label,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "required": required,
        "completed": completed,
        "remaining": remaining,
        "is_complete": is_complete,
        "message": (
            f"{role_label} weekly target completed ({completed}/{required})."
            if is_complete
            else f"{role_label} weekly target pending: {remaining} more inspection(s) required ({completed}/{required} done)."
        ),
    }


def _action_required_counts(db: Session, user: User) -> dict:
    query = db.query(Inspection).filter(
        Inspection.submitted_by == user.id,
        Inspection.status.in_([InspectionStatus.DRAFT, InspectionStatus.RETURNED_FOR_CLARIFICATION]),
    )
    draft = query.filter(Inspection.status == InspectionStatus.DRAFT).count()
    returned = query.filter(Inspection.status == InspectionStatus.RETURNED_FOR_CLARIFICATION).count()
    return {
        "total": draft + returned,
        "draft": draft,
        "returned": returned,
    }


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
    items = query.limit(limit).all()
    for item in items:
        _attach_kpi_category(db, item)
    return [_row(i) for i in items]


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
    for item in items:
        _attach_kpi_category(db, item)
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


@router.get("/login-notification-summary")
def login_notification_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Compact login notification payload for inspector weekly targets and action items.

    SM/EIT users receive their weekly inspection completion status plus any draft or
    returned inspections. Reviewer roles continue to use /reviews/pending for their
    queue count, but this endpoint remains safe for every role.
    """

    weekly_target = _weekly_target_summary(db, user)
    action_required = _action_required_counts(db, user)
    return {
        "current_role": user.role.code.value if user.role else None,
        "weekly_target": weekly_target,
        "action_required": action_required,
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
                "kpi_categories": [
                    {"code": KPI_6_CLEANLINESS, "label": "KPI-6 Level of Cleanliness"},
                    {"code": KPI_CHEMICALS, "label": "KPI Chemicals & Consumables"},
                ],
                "stations": [],
                "message": "No stations are directly mapped to this user.",
            }
        query = query.filter(Station.id.in_(station_ids))

    stations = [_station_contract_status(db, station) for station in query.all()]
    return {
        "current_role": user.role.code.value if user.role else None,
        "inspection_type": _inspection_type_for_user(user).value,
        "kpi_categories": [
            {"code": KPI_6_CLEANLINESS, "label": "KPI-6 Level of Cleanliness"},
            {"code": KPI_CHEMICALS, "label": "KPI Chemicals & Consumables"},
        ],
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
    inspection = create_inspection(db, payload, user)
    _set_kpi_category(db, inspection, payload.kpi_category)
    db.commit()
    db.refresh(inspection)
    return _attach_kpi_category(db, inspection)


@router.get("/{inspection_id}", response_model=InspectionOut)
def get_inspection(inspection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    require_inspection_access(db, user, inspection)
    return _attach_kpi_category(db, inspection)


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

    effective_captured_at = captured_at or datetime.utcnow()
    try:
        stamped_data, stamped_content_type = prepare_evidence_media(
            media_type=media_type,
            data=data,
            content_type=file.content_type,
            captured_at=effective_captured_at,
            captured_latitude=captured_latitude,
            captured_longitude=captured_longitude,
            gps_accuracy=gps_accuracy,
        )
    except EvidenceProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    checksum = sha256_bytes(stamped_data)
    object_path = build_object_path(inspection.contract_id, inspection.station_id, inspection.id, f"entry-{entry.id}-{file.filename or 'upload.bin'}")
    upload_bytes(object_path, stamped_data, stamped_content_type or file.content_type)
    row = InspectionMedia(
        inspection_id=inspection.id,
        inspection_entry_id=entry.id,
        attribute_id=entry.attribute_id,
        sub_area_id=entry.sub_area_id,
        media_type=media_type,
        object_path=object_path,
        original_file_name=file.filename or "upload.bin",
        mime_type=stamped_content_type or file.content_type,
        file_size=len(stamped_data),
        checksum=checksum,
        captured_latitude=captured_latitude,
        captured_longitude=captured_longitude,
        gps_accuracy=gps_accuracy,
        captured_at=effective_captured_at,
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

    effective_captured_at = captured_at or datetime.utcnow()
    try:
        stamped_data, stamped_content_type = prepare_evidence_media(
            media_type=media_type,
            data=data,
            content_type=file.content_type,
            captured_at=effective_captured_at,
            captured_latitude=captured_latitude,
            captured_longitude=captured_longitude,
            gps_accuracy=gps_accuracy,
        )
    except EvidenceProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    checksum = sha256_bytes(stamped_data)
    object_path = build_object_path(inspection.contract_id, inspection.station_id, inspection.id, file.filename or "upload.bin")
    upload_bytes(object_path, stamped_data, stamped_content_type or file.content_type)
    row = InspectionMedia(
        inspection_id=inspection.id,
        attribute_id=attribute_id,
        sub_area_id=sub_area_id,
        media_type=media_type,
        object_path=object_path,
        original_file_name=file.filename or "upload.bin",
        mime_type=stamped_content_type or file.content_type,
        file_size=len(stamped_data),
        checksum=checksum,
        captured_latitude=captured_latitude,
        captured_longitude=captured_longitude,
        gps_accuracy=gps_accuracy,
        captured_at=effective_captured_at,
        uploaded_by=user.id,
        processing_status="UPLOADED",
    )
    db.add(row)
    audit_log(db, actor=user, action="MEDIA_UPLOADED", entity_type="Inspection", entity_id=inspection.id, new_value={"object_path": object_path})
    db.commit()
    db.refresh(row)
    return row
