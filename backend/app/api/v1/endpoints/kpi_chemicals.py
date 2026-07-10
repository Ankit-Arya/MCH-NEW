from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import MASTER_ADMIN_ROLES, require_roles, require_inspection_access, require_station_access
from app.models.all_models import Inspection, InspectionStatus, InspectionWorkflowHistory, Station, User
from app.models.kpi_chemical import (
    ChemicalInspectionEntry,
    InspectionKpiContext,
    KPI_6_CLEANLINESS,
    KPI_CHEMICALS,
    KpiChemical,
    StationChemicalRequirement,
)
from app.services.audit_service import audit_log
from app.services.inspection_service import require_inspection_station_access_for_edit
from app.schemas.inspection import InspectionOut

router = APIRouter()


class ChemicalCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=200)
    unit: str = Field("Ltr/Kg/No", min_length=1, max_length=40)
    default_required_quantity: float = Field(0, ge=0)
    description: str | None = None
    sort_order: int = Field(1, ge=1)


class ChemicalUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    unit: str | None = Field(default=None, min_length=1, max_length=40)
    default_required_quantity: float | None = Field(default=None, ge=0)
    description: str | None = None
    sort_order: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class StationRequirementIn(BaseModel):
    chemical_id: int
    required_quantity: float = Field(..., ge=0)
    unit: str | None = Field(default=None, max_length=40)
    remarks: str | None = None


class StationRequirementUpdate(BaseModel):
    required_quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    remarks: str | None = None
    is_active: bool | None = None


class ChemicalEntryIn(BaseModel):
    chemical_id: int
    actual_quantity: float = Field(..., ge=0)
    remarks: str | None = None
    captured_latitude: float | None = None
    captured_longitude: float | None = None
    gps_accuracy: float | None = None
    captured_at: datetime | None = None


class ChemicalSubmitIn(BaseModel):
    remarks: str | None = None


def _require_manage(user: User) -> None:
    require_roles(user, MASTER_ADMIN_ROLES)


def _as_dict(obj) -> dict:
    return {col.name: getattr(obj, col.name) for col in obj.__table__.columns}


def _commit_or_409(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate/invalid chemical master mapping. Please check station and chemical.") from exc


def _chemical_row(row: KpiChemical) -> dict:
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "unit": row.unit,
        "default_required_quantity": row.default_required_quantity,
        "description": row.description,
        "sort_order": row.sort_order,
        "is_active": row.is_active,
    }


def _requirement_row(row: StationChemicalRequirement) -> dict:
    chemical = row.chemical
    return {
        "id": row.id,
        "station_id": row.station_id,
        "chemical_id": row.chemical_id,
        "chemical_code": chemical.code if chemical else None,
        "chemical_name": chemical.name if chemical else None,
        "required_quantity": row.required_quantity,
        "unit": row.unit or (chemical.unit if chemical else None),
        "remarks": row.remarks,
        "is_active": row.is_active,
    }


def _context_for(db: Session, inspection_id: int) -> InspectionKpiContext:
    ctx = db.query(InspectionKpiContext).filter_by(inspection_id=inspection_id).first()
    if not ctx:
        ctx = InspectionKpiContext(inspection_id=inspection_id, kpi_category=KPI_6_CLEANLINESS)
        db.add(ctx)
        db.flush()
    return ctx


def _ensure_chemical_inspection(db: Session, inspection: Inspection) -> None:
    ctx = _context_for(db, inspection.id)
    if ctx.kpi_category != KPI_CHEMICALS:
        raise HTTPException(status_code=400, detail="This inspection is not a Chemicals & Consumables KPI inspection")


def _ensure_editable(db: Session, inspection: Inspection, user: User) -> None:
    _ensure_chemical_inspection(db, inspection)
    if inspection.status not in [InspectionStatus.DRAFT, InspectionStatus.RETURNED_FOR_CLARIFICATION]:
        raise HTTPException(status_code=400, detail="Chemical entries can be edited only while inspection is draft/returned")
    require_inspection_station_access_for_edit(db, user, inspection)


def _requirement_for(db: Session, station_id: int, chemical_id: int) -> StationChemicalRequirement:
    row = (
        db.query(StationChemicalRequirement)
        .join(KpiChemical, KpiChemical.id == StationChemicalRequirement.chemical_id)
        .filter(
            StationChemicalRequirement.station_id == station_id,
            StationChemicalRequirement.chemical_id == chemical_id,
            StationChemicalRequirement.is_active.is_(True),
            KpiChemical.is_active.is_(True),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=400, detail="Selected chemical is not mapped as active requirement for this station")
    return row


def _calculate(required: float, actual: float) -> tuple[float, float, float]:
    required = max(float(required or 0), 0)
    actual = max(float(actual or 0), 0)
    shortfall = max(required - actual, 0)
    excess = max(actual - required, 0)
    availability = 100 if required == 0 else round(min(actual, required) / required * 100, 2)
    return shortfall, excess, availability


def _entry_row(row: ChemicalInspectionEntry) -> dict:
    chemical = row.chemical
    difference = round((row.actual_quantity or 0) - (row.required_quantity or 0), 2)
    return {
        "id": row.id,
        "inspection_id": row.inspection_id,
        "station_id": row.station_id,
        "chemical_id": row.chemical_id,
        "chemical_code": chemical.code if chemical else None,
        "chemical_name": chemical.name if chemical else None,
        "unit": chemical.unit if chemical else None,
        "required_quantity": row.required_quantity,
        "actual_quantity": row.actual_quantity,
        "difference_quantity": difference,
        "shortfall_quantity": row.shortfall_quantity,
        "excess_quantity": row.excess_quantity,
        "availability_percent": row.availability_percent,
        "remarks": row.remarks,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "is_deleted": row.is_deleted,
    }


def _summary(entries: list[ChemicalInspectionEntry]) -> dict:
    required_total = sum(float(row.required_quantity or 0) for row in entries if not row.is_deleted)
    actual_capped_total = sum(min(float(row.actual_quantity or 0), float(row.required_quantity or 0)) for row in entries if not row.is_deleted)
    actual_total = sum(float(row.actual_quantity or 0) for row in entries if not row.is_deleted)
    shortfall_total = sum(float(row.shortfall_quantity or 0) for row in entries if not row.is_deleted)
    score = 100 if required_total == 0 else round(actual_capped_total / required_total * 100, 2)
    return {
        "required_total": round(required_total, 2),
        "actual_total": round(actual_total, 2),
        "shortfall_total": round(shortfall_total, 2),
        "score_percent": score,
        "pass_threshold_percent": 90,
        "is_below_threshold": score < 90,
    }


@router.get("/chemicals")
def list_chemicals(include_inactive: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(KpiChemical).order_by(KpiChemical.sort_order, KpiChemical.name)
    if not include_inactive:
        query = query.filter(KpiChemical.is_active.is_(True))
    return [_chemical_row(row) for row in query.all()]


@router.post("/chemicals")
def create_chemical(payload: ChemicalCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    row = KpiChemical(**payload.model_dump())
    db.add(row)
    db.flush()
    audit_log(db, actor=user, action="MASTER_KPI_CHEMICAL_CREATED", entity_type="KpiChemical", entity_id=row.id, new_value=_as_dict(row))
    _commit_or_409(db)
    db.refresh(row)
    return _chemical_row(row)


@router.put("/chemicals/{chemical_id}")
def update_chemical(chemical_id: int, payload: ChemicalUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    row = db.get(KpiChemical, chemical_id)
    if not row:
        raise HTTPException(status_code=404, detail="Chemical not found")
    old = _as_dict(row)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.flush()
    audit_log(db, actor=user, action="MASTER_KPI_CHEMICAL_UPDATED", entity_type="KpiChemical", entity_id=row.id, old_value=old, new_value=_as_dict(row))
    _commit_or_409(db)
    db.refresh(row)
    return _chemical_row(row)


@router.delete("/chemicals/{chemical_id}")
def deactivate_chemical(chemical_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    row = db.get(KpiChemical, chemical_id)
    if not row:
        raise HTTPException(status_code=404, detail="Chemical not found")
    row.is_active = False
    db.flush()
    _commit_or_409(db)
    return {"message": "Chemical deactivated", "id": chemical_id}


@router.get("/stations/{station_id}/requirements")
def list_station_requirements(station_id: int, include_inactive: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_station_access(db, user, station_id)
    query = db.query(StationChemicalRequirement).join(KpiChemical).filter(StationChemicalRequirement.station_id == station_id).order_by(KpiChemical.sort_order, KpiChemical.name)
    if not include_inactive:
        query = query.filter(StationChemicalRequirement.is_active.is_(True), KpiChemical.is_active.is_(True))
    return [_requirement_row(row) for row in query.all()]


@router.post("/stations/{station_id}/requirements")
def save_station_requirement(station_id: int, payload: StationRequirementIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    station = db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    chemical = db.get(KpiChemical, payload.chemical_id)
    if not chemical:
        raise HTTPException(status_code=404, detail="Chemical not found")
    row = db.query(StationChemicalRequirement).filter_by(station_id=station_id, chemical_id=payload.chemical_id).first()
    if row:
        row.required_quantity = payload.required_quantity
        row.unit = payload.unit
        row.remarks = payload.remarks
        row.is_active = True
    else:
        row = StationChemicalRequirement(station_id=station_id, **payload.model_dump())
        db.add(row)
    db.flush()
    audit_log(db, actor=user, action="MASTER_STATION_CHEMICAL_REQUIREMENT_SAVED", entity_type="StationChemicalRequirement", entity_id=row.id, new_value=_as_dict(row))
    _commit_or_409(db)
    db.refresh(row)
    return _requirement_row(row)


@router.put("/station-requirements/{requirement_id}")
def update_station_requirement(requirement_id: int, payload: StationRequirementUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    row = db.get(StationChemicalRequirement, requirement_id)
    if not row:
        raise HTTPException(status_code=404, detail="Station chemical requirement not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.flush()
    _commit_or_409(db)
    db.refresh(row)
    return _requirement_row(row)


@router.delete("/station-requirements/{requirement_id}")
def deactivate_station_requirement(requirement_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    row = db.get(StationChemicalRequirement, requirement_id)
    if not row:
        raise HTTPException(status_code=404, detail="Station chemical requirement not found")
    row.is_active = False
    db.flush()
    _commit_or_409(db)
    return {"message": "Station chemical requirement deactivated", "id": requirement_id}


@router.get("/inspections/{inspection_id}/requirements")
def inspection_requirements(inspection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    require_inspection_access(db, user, inspection)
    _ensure_chemical_inspection(db, inspection)
    requirements = [
        _requirement_row(row)
        for row in db.query(StationChemicalRequirement)
        .join(KpiChemical, KpiChemical.id == StationChemicalRequirement.chemical_id)
        .filter(
            StationChemicalRequirement.station_id == inspection.station_id,
            StationChemicalRequirement.is_active.is_(True),
            KpiChemical.is_active.is_(True),
        )
        .order_by(KpiChemical.sort_order, KpiChemical.name)
        .all()
    ]
    entries = {
        row.chemical_id: _entry_row(row)
        for row in db.query(ChemicalInspectionEntry).filter_by(inspection_id=inspection.id, is_deleted=False).all()
    }
    return [{**row, "entry": entries.get(row["chemical_id"])} for row in requirements]


@router.get("/inspections/{inspection_id}/entries")
def list_inspection_entries(inspection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    require_inspection_access(db, user, inspection)
    _ensure_chemical_inspection(db, inspection)
    entries = db.query(ChemicalInspectionEntry).filter_by(inspection_id=inspection.id, is_deleted=False).order_by(ChemicalInspectionEntry.id).all()
    return {"items": [_entry_row(row) for row in entries], "summary": _summary(entries)}


@router.post("/inspections/{inspection_id}/entries")
def save_inspection_entry(inspection_id: int, payload: ChemicalEntryIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    _ensure_editable(db, inspection, user)
    requirement = _requirement_for(db, inspection.station_id, payload.chemical_id)
    shortfall, excess, availability = _calculate(requirement.required_quantity, payload.actual_quantity)
    row = db.query(ChemicalInspectionEntry).filter_by(inspection_id=inspection.id, chemical_id=payload.chemical_id).first()
    if row:
        row.required_quantity = requirement.required_quantity
        row.actual_quantity = payload.actual_quantity
        row.shortfall_quantity = shortfall
        row.excess_quantity = excess
        row.availability_percent = availability
        row.remarks = payload.remarks
        row.captured_latitude = payload.captured_latitude
        row.captured_longitude = payload.captured_longitude
        row.gps_accuracy = payload.gps_accuracy
        row.captured_at = payload.captured_at or datetime.utcnow()
        row.is_deleted = False
    else:
        row = ChemicalInspectionEntry(
            inspection_id=inspection.id,
            station_id=inspection.station_id,
            chemical_id=payload.chemical_id,
            required_quantity=requirement.required_quantity,
            actual_quantity=payload.actual_quantity,
            shortfall_quantity=shortfall,
            excess_quantity=excess,
            availability_percent=availability,
            remarks=payload.remarks,
            captured_latitude=payload.captured_latitude,
            captured_longitude=payload.captured_longitude,
            gps_accuracy=payload.gps_accuracy,
            captured_at=payload.captured_at or datetime.utcnow(),
            created_by=user.id,
        )
        db.add(row)
    db.flush()
    audit_log(db, actor=user, action="KPI_CHEMICAL_ENTRY_SAVED", entity_type="ChemicalInspectionEntry", entity_id=row.id, new_value=_as_dict(row))
    _commit_or_409(db)
    db.refresh(row)
    return _entry_row(row)


@router.delete("/inspections/{inspection_id}/entries/{entry_id}")
def delete_inspection_entry(inspection_id: int, entry_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    _ensure_editable(db, inspection, user)
    row = db.get(ChemicalInspectionEntry, entry_id)
    if not row or row.inspection_id != inspection.id or row.is_deleted:
        raise HTTPException(status_code=404, detail="Chemical inspection entry not found")
    row.is_deleted = True
    db.flush()
    _commit_or_409(db)
    return {"message": "Chemical entry deleted", "id": entry_id}


@router.get("/inspections/{inspection_id}/summary")
def chemical_inspection_summary(inspection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    require_inspection_access(db, user, inspection)
    _ensure_chemical_inspection(db, inspection)
    entries = db.query(ChemicalInspectionEntry).filter_by(inspection_id=inspection.id, is_deleted=False).all()
    return _summary(entries)


@router.post("/inspections/{inspection_id}/submit", response_model=InspectionOut)
def submit_chemical_inspection(inspection_id: int, payload: ChemicalSubmitIn | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    _ensure_editable(db, inspection, user)
    entries = db.query(ChemicalInspectionEntry).filter_by(inspection_id=inspection.id, is_deleted=False).all()
    if not entries:
        raise HTTPException(status_code=400, detail="Add at least one chemical quantity entry before submitting")
    if payload and payload.remarks is not None:
        inspection.remarks = payload.remarks
    old_status = inspection.status.value
    inspection.status = InspectionStatus.UNDER_LINE_MANAGER_REVIEW
    inspection.submitted_at = datetime.utcnow()
    db.add(InspectionWorkflowHistory(
        inspection_id=inspection.id,
        from_status=old_status,
        to_status=inspection.status.value,
        action_by=user.id,
        action="SUBMIT_KPI_CHEMICALS",
        remarks="Chemicals & Consumables KPI inspection submitted for Line Manager review",
    ))
    audit_log(db, actor=user, action="KPI_CHEMICAL_INSPECTION_SUBMITTED", entity_type="Inspection", entity_id=inspection.id)
    _commit_or_409(db)
    db.refresh(inspection)
    setattr(inspection, "kpi_category", KPI_CHEMICALS)
    return inspection
