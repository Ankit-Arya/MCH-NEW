from datetime import datetime, date
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.all_models import (
    ContractStation,
    GradingOption,
    Inspection,
    InspectionAttribute,
    InspectionAttributeScore,
    InspectionMedia,
    InspectionStatus,
    InspectionSubArea,
    InspectionSubAreaObservation,
    InspectionWorkflowHistory,
    MediaType,
    User,
)
from app.schemas.inspection import InspectionStartIn, InspectionDraftIn
from app.core.permissions import require_station_access
from app.services.audit_service import audit_log


def generate_inspection_no(station_id: int, user_id: int) -> str:
    return f"INSP-{datetime.utcnow():%Y%m%d%H%M%S}-{station_id}-{user_id}"


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


def save_draft(db: Session, inspection: Inspection, payload: InspectionDraftIn, user: User) -> Inspection:
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


def submit_inspection(db: Session, inspection: Inspection, payload: InspectionDraftIn, user: User) -> Inspection:
    inspection = save_draft(db, inspection, payload, user)
    attributes = db.query(InspectionAttribute).filter_by(is_active=True).all()
    scored_attribute_ids = {s.attribute_id for s in inspection.attribute_scores}
    missing = [a.name for a in attributes if a.id not in scored_attribute_ids]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing grading for attributes: {', '.join(missing)}")

    # Evidence validation: each applicable sub-area must have configured minimum photos.
    # If a sub-area is not applicable, a reason must be recorded.
    observations = {o.sub_area_id: o for o in inspection.observations}
    sub_areas = db.query(InspectionSubArea).filter_by(is_active=True).all()
    for sub_area in sub_areas:
        obs = observations.get(sub_area.id)
        if obs and obs.is_applicable is False:
            if sub_area.allow_na and obs.na_reason:
                continue
            raise HTTPException(status_code=400, detail=f"N/A reason is required for {sub_area.name}")
        photo_count = db.query(InspectionMedia).filter_by(inspection_id=inspection.id, sub_area_id=sub_area.id, media_type=MediaType.PHOTO, is_deleted=False).count()
        if photo_count < sub_area.photo_min_required:
            raise HTTPException(status_code=400, detail=f"At least {sub_area.photo_min_required} photo(s) required for {sub_area.name}")

    old_status = inspection.status.value
    inspection.status = InspectionStatus.UNDER_LINE_MANAGER_REVIEW
    inspection.submitted_at = datetime.utcnow()
    db.add(InspectionWorkflowHistory(inspection_id=inspection.id, from_status=old_status, to_status=inspection.status.value, action_by=user.id, action="SUBMIT", remarks="Submitted for Line Manager review"))
    audit_log(db, actor=user, action="INSPECTION_SUBMITTED", entity_type="Inspection", entity_id=inspection.id, old_value={"status": old_status}, new_value={"status": inspection.status.value})
    db.commit()
    db.refresh(inspection)
    return inspection
