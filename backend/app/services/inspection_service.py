from datetime import datetime, date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.all_models import (
    ContractStation,
    GradingOption,
    Inspection,
    InspectionAttribute,
    InspectionAttributeScore,
    InspectionEntry,
    InspectionMedia,
    InspectionStatus,
    InspectionSubArea,
    InspectionSubAreaObservation,
    InspectionWorkflowHistory,
    MediaType,
    User,
)
from app.schemas.inspection import InspectionStartIn, InspectionDraftIn, InspectionEntryCreate
from app.core.permissions import require_station_access
from app.services.audit_service import audit_log


def generate_inspection_no(station_id: int, user_id: int) -> str:
    return f"INSP-{datetime.utcnow():%Y%m%d%H%M%S}-{station_id}-{user_id}"


def generate_entry_no(db: Session, inspection_id: int) -> str:
    count = db.query(InspectionEntry).filter(
        InspectionEntry.inspection_id == inspection_id,
        InspectionEntry.is_deleted == False,  # noqa: E712
    ).count()
    return f"ENT-{count + 1:04d}"


def create_inspection(db: Session, payload: InspectionStartIn, user: User) -> Inspection:
    require_station_access(db, user, payload.station_id)
    mapping = db.query(ContractStation).filter_by(contract_id=payload.contract_id, station_id=payload.station_id, is_active=True).first()
    if not mapping:
        raise HTTPException(status_code=400, detail="Station is not mapped to selected contract")
    now = datetime.utcnow()
    inspection = Inspection(
        inspection_no=generate_inspection_no(payload.station_id, user.id),
        contract_id=payload.contract_id,
        station_id=payload.station_id,
        inspection_type=payload.inspection_type,
        inspection_date=date.today(),
        started_at=now,
        submitted_by=user.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        gps_accuracy=payload.gps_accuracy,
        device_info=payload.device_info,
        remarks=payload.remarks,
        is_before_10am=now.hour < 10,
        is_late=now.hour >= 10 and payload.inspection_type.value == "SM_INSPECTION",
    )
    db.add(inspection)
    db.flush()
    db.add(InspectionWorkflowHistory(inspection_id=inspection.id, from_status=None, to_status=InspectionStatus.DRAFT.value, action_by=user.id, action="START", remarks="Inspection started"))
    audit_log(db, actor=user, action="INSPECTION_STARTED", entity_type="Inspection", entity_id=inspection.id)
    db.commit()
    db.refresh(inspection)
    return inspection


def _grade_for_inspection(db: Session, inspection: Inspection, grade_code: str) -> GradingOption:
    grade = db.query(GradingOption).filter(
        GradingOption.scheme_id == inspection.contract.grading_scheme_id,
        GradingOption.grade_code == grade_code,
    ).first()
    if not grade:
        raise HTTPException(status_code=400, detail=f"Invalid grade {grade_code} for this contract grading scheme")
    return grade


def save_entry(db: Session, inspection: Inspection, payload: InspectionEntryCreate, user: User) -> InspectionEntry:
    if inspection.status not in [InspectionStatus.DRAFT, InspectionStatus.RETURNED_FOR_CLARIFICATION]:
        raise HTTPException(status_code=400, detail="Entries can be added only while inspection is draft/returned")
    require_station_access(db, user, inspection.station_id)

    attribute = db.get(InspectionAttribute, payload.attribute_id)
    if not attribute or not attribute.is_active:
        raise HTTPException(status_code=400, detail="Invalid inspection attribute")
    sub_area = db.get(InspectionSubArea, payload.sub_area_id)
    if not sub_area or not sub_area.is_active or sub_area.attribute_id != attribute.id:
        raise HTTPException(status_code=400, detail="Invalid sub-area for selected attribute")
    grade = _grade_for_inspection(db, inspection, payload.grade_code)

    entry = InspectionEntry(
        inspection_id=inspection.id,
        entry_no=generate_entry_no(db, inspection.id),
        attribute_id=attribute.id,
        sub_area_id=sub_area.id,
        grade_code=grade.grade_code,
        grade_percentage=grade.percentage,
        remarks=payload.remarks,
        captured_latitude=payload.captured_latitude,
        captured_longitude=payload.captured_longitude,
        gps_accuracy=payload.gps_accuracy,
        captured_at=payload.captured_at or datetime.utcnow(),
        created_by=user.id,
    )
    db.add(entry)
    db.flush()
    audit_log(db, actor=user, action="INSPECTION_ENTRY_CREATED", entity_type="InspectionEntry", entity_id=entry.id, new_value={"inspection_id": inspection.id, "entry_no": entry.entry_no})
    db.commit()
    db.refresh(entry)
    return entry


def entry_to_dict(db: Session, entry: InspectionEntry) -> dict:
    photo_count = db.query(InspectionMedia).filter_by(
        inspection_entry_id=entry.id,
        media_type=MediaType.PHOTO,
        is_deleted=False,
    ).count()
    video_count = db.query(InspectionMedia).filter_by(
        inspection_entry_id=entry.id,
        media_type=MediaType.VIDEO,
        is_deleted=False,
    ).count()
    return {
        "id": entry.id,
        "inspection_id": entry.inspection_id,
        "entry_no": entry.entry_no,
        "attribute_id": entry.attribute_id,
        "attribute_name": entry.attribute.name if entry.attribute else None,
        "sub_area_id": entry.sub_area_id,
        "sub_area_name": entry.sub_area.name if entry.sub_area else None,
        "grade_code": entry.grade_code,
        "grade_percentage": entry.grade_percentage,
        "remarks": entry.remarks,
        "captured_latitude": entry.captured_latitude,
        "captured_longitude": entry.captured_longitude,
        "gps_accuracy": entry.gps_accuracy,
        "captured_at": entry.captured_at,
        "created_by": entry.created_by,
        "created_at": entry.created_at,
        "photo_count": photo_count,
        "video_count": video_count,
    }


def list_entries(db: Session, inspection_id: int) -> list[dict]:
    entries = db.query(InspectionEntry).filter(
        InspectionEntry.inspection_id == inspection_id,
        InspectionEntry.is_deleted == False,  # noqa: E712
    ).order_by(InspectionEntry.id).all()
    return [entry_to_dict(db, e) for e in entries]


def soft_delete_entry(db: Session, inspection: Inspection, entry_id: int, user: User) -> None:
    if inspection.status not in [InspectionStatus.DRAFT, InspectionStatus.RETURNED_FOR_CLARIFICATION]:
        raise HTTPException(status_code=400, detail="Entries can be deleted only before submission")
    require_station_access(db, user, inspection.station_id)
    entry = db.get(InspectionEntry, entry_id)
    if not entry or entry.inspection_id != inspection.id or entry.is_deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry.is_deleted = True
    for media in entry.media:
        media.is_deleted = True
    audit_log(db, actor=user, action="INSPECTION_ENTRY_DELETED", entity_type="InspectionEntry", entity_id=entry.id)
    db.commit()


def save_draft(db: Session, inspection: Inspection, payload: InspectionDraftIn, user: User) -> Inspection:
    """Legacy checklist draft save retained for backward compatibility.

    New entry-based UI does not call this route.
    """
    if inspection.status not in [InspectionStatus.DRAFT, InspectionStatus.RETURNED_FOR_CLARIFICATION]:
        raise HTTPException(status_code=400, detail="Only draft or returned inspection can be edited")
    require_station_access(db, user, inspection.station_id)

    grading_options = {
        (g.scheme_id, g.grade_code): g for g in db.query(GradingOption).filter(GradingOption.scheme_id == inspection.contract.grading_scheme_id).all()
    }
    for score_in in payload.attribute_scores:
        grade = grading_options.get((inspection.contract.grading_scheme_id, score_in.grade_code))
        if not grade:
            raise HTTPException(status_code=400, detail=f"Invalid grade {score_in.grade_code}")
        row = db.query(InspectionAttributeScore).filter_by(inspection_id=inspection.id, attribute_id=score_in.attribute_id).first()
        if not row:
            row = InspectionAttributeScore(inspection_id=inspection.id, attribute_id=score_in.attribute_id, grade_code=score_in.grade_code, grade_percentage=grade.percentage, remarks=score_in.remarks)
            db.add(row)
        else:
            row.grade_code = score_in.grade_code
            row.grade_percentage = grade.percentage
            row.remarks = score_in.remarks

    for obs_in in payload.observations:
        row = db.query(InspectionSubAreaObservation).filter_by(inspection_id=inspection.id, sub_area_id=obs_in.sub_area_id).first()
        if not row:
            row = InspectionSubAreaObservation(**obs_in.model_dump(), inspection_id=inspection.id)
            db.add(row)
        else:
            row.is_applicable = obs_in.is_applicable
            row.na_reason = obs_in.na_reason
            row.observation_text = obs_in.observation_text
    if payload.remarks is not None:
        inspection.remarks = payload.remarks
    audit_log(db, actor=user, action="INSPECTION_DRAFT_SAVED", entity_type="Inspection", entity_id=inspection.id)
    db.commit()
    db.refresh(inspection)
    return inspection


def submit_entry_based_inspection(db: Session, inspection: Inspection, user: User, remarks: str | None = None) -> Inspection:
    if inspection.status not in [InspectionStatus.DRAFT, InspectionStatus.RETURNED_FOR_CLARIFICATION]:
        raise HTTPException(status_code=400, detail="Only draft or returned inspection can be submitted")
    require_station_access(db, user, inspection.station_id)

    entries = db.query(InspectionEntry).filter(
        InspectionEntry.inspection_id == inspection.id,
        InspectionEntry.is_deleted == False,  # noqa: E712
    ).order_by(InspectionEntry.id).all()
    if not entries:
        raise HTTPException(status_code=400, detail="Add at least one inspection entry before submitting")

    missing_photo = []
    for entry in entries:
        photo_count = db.query(InspectionMedia).filter_by(
            inspection_entry_id=entry.id,
            media_type=MediaType.PHOTO,
            is_deleted=False,
        ).count()
        if photo_count < 1:
            missing_photo.append(f"{entry.entry_no} - {entry.attribute.name if entry.attribute else entry.attribute_id} / {entry.sub_area.name if entry.sub_area else entry.sub_area_id}")
    if missing_photo:
        raise HTTPException(status_code=400, detail="Photo evidence required for: " + "; ".join(missing_photo))

    if remarks is not None:
        inspection.remarks = remarks
    old_status = inspection.status.value
    inspection.status = InspectionStatus.UNDER_LINE_MANAGER_REVIEW
    inspection.submitted_at = datetime.utcnow()
    db.add(InspectionWorkflowHistory(inspection_id=inspection.id, from_status=old_status, to_status=inspection.status.value, action_by=user.id, action="SUBMIT", remarks="Entry-based inspection submitted for Line Manager review"))
    audit_log(db, actor=user, action="INSPECTION_SUBMITTED", entity_type="Inspection", entity_id=inspection.id, old_value={"status": old_status}, new_value={"status": inspection.status.value, "entry_count": len(entries)})
    db.commit()
    db.refresh(inspection)
    return inspection


def submit_inspection(db: Session, inspection: Inspection, payload: InspectionDraftIn, user: User) -> Inspection:
    """Legacy checklist submit retained for older screens/API clients."""
    inspection = save_draft(db, inspection, payload, user)
    attributes = db.query(InspectionAttribute).filter_by(is_active=True).all()
    scored_attribute_ids = {s.attribute_id for s in inspection.attribute_scores}
    missing = [a.name for a in attributes if a.id not in scored_attribute_ids]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing grading for attributes: {', '.join(missing)}")

    old_status = inspection.status.value
    inspection.status = InspectionStatus.UNDER_LINE_MANAGER_REVIEW
    inspection.submitted_at = datetime.utcnow()
    db.add(InspectionWorkflowHistory(inspection_id=inspection.id, from_status=old_status, to_status=inspection.status.value, action_by=user.id, action="SUBMIT", remarks="Submitted for Line Manager review"))
    audit_log(db, actor=user, action="INSPECTION_SUBMITTED", entity_type="Inspection", entity_id=inspection.id, old_value={"status": old_status}, new_value={"status": inspection.status.value})
    db.commit()
    db.refresh(inspection)
    return inspection
