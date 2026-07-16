from __future__ import annotations

from typing import Any, Type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles, get_accessible_station_ids, get_accessible_contract_ids, get_scope_user_ids, is_admin_scope
from app.models.all_models import (
    BillingCycle,
    Contract,
    Contractor,
    ContractStation,
    GradingOption,
    GradingScheme,
    InspectionAttribute,
    InspectionSubArea,
    Line,
    RoleCode,
    Station,
    User,
)
from app.schemas.master import (
    ContractCreate,
    ContractOut,
    ContractStationCreate,
    ContractStationOut,
    ContractUpdate,
    ContractorCreate,
    ContractorOut,
    ContractorUpdate,
    GradingOptionCreate,
    GradingOptionOut,
    GradingOptionUpdate,
    GradingSchemeCreate,
    GradingSchemeOut,
    GradingSchemeUpdate,
    InspectionAttributeCreate,
    InspectionAttributeOut,
    InspectionAttributeUpdate,
    InspectionSubAreaCreate,
    InspectionSubAreaOut,
    InspectionSubAreaUpdate,
    LineCreate,
    LineOut,
    LineUpdate,
    StationCreate,
    StationOut,
    StationUpdate,
)
from app.services.audit_service import audit_log

router = APIRouter()

MASTER_ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN}


def _safe_user(u: User) -> dict[str, Any]:
    return {
        "id": u.id,
        "username": u.username,
        "name": u.name,
        "emp_number": u.emp_number,
        "role": u.role.code.value if u.role else None,
    }


def _can_manage(user: User) -> bool:
    return bool(user.role and user.role.code in MASTER_ADMIN_ROLES)


def _require_manage(user: User) -> None:
    require_roles(user, MASTER_ADMIN_ROLES)


def _as_dict(obj: Any) -> dict[str, Any]:
    return {col.name: getattr(obj, col.name) for col in obj.__table__.columns}


def _commit_or_409(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate/invalid master data. Please check unique codes and linked records.",
        ) from exc


def _get_or_404(db: Session, model: Type[Any], obj_id: int) -> Any:
    obj = db.get(model, obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


def _create(db: Session, user: User, model: Type[Any], payload: Any, entity_type: str) -> Any:
    _require_manage(user)
    obj = model(**payload.model_dump())
    db.add(obj)
    db.flush()
    audit_log(db, actor=user, action=f"MASTER_{entity_type}_CREATED", entity_type=entity_type, entity_id=obj.id, new_value=_as_dict(obj))
    _commit_or_409(db)
    db.refresh(obj)
    return obj


def _update(db: Session, user: User, model: Type[Any], obj_id: int, payload: Any, entity_type: str) -> Any:
    _require_manage(user)
    obj = _get_or_404(db, model, obj_id)
    old_value = _as_dict(obj)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.flush()
    audit_log(db, actor=user, action=f"MASTER_{entity_type}_UPDATED", entity_type=entity_type, entity_id=obj.id, old_value=old_value, new_value=_as_dict(obj))
    _commit_or_409(db)
    db.refresh(obj)
    return obj


def _deactivate(db: Session, user: User, model: Type[Any], obj_id: int, entity_type: str) -> dict[str, Any]:
    _require_manage(user)
    obj = _get_or_404(db, model, obj_id)
    if not hasattr(obj, "is_active"):
        raise HTTPException(status_code=400, detail="This master data cannot be deactivated")
    old_value = _as_dict(obj)
    obj.is_active = False
    db.flush()
    audit_log(db, actor=user, action=f"MASTER_{entity_type}_DEACTIVATED", entity_type=entity_type, entity_id=obj.id, old_value=old_value, new_value=_as_dict(obj))
    _commit_or_409(db)
    return {"message": f"{entity_type} deactivated", "id": obj_id}


def _activate(db: Session, user: User, model: Type[Any], obj_id: int, entity_type: str) -> dict[str, Any]:
    _require_manage(user)
    obj = _get_or_404(db, model, obj_id)
    if not hasattr(obj, "is_active"):
        raise HTTPException(status_code=400, detail="This master data cannot be activated")
    old_value = _as_dict(obj)
    obj.is_active = True
    db.flush()
    audit_log(db, actor=user, action=f"MASTER_{entity_type}_ACTIVATED", entity_type=entity_type, entity_id=obj.id, old_value=old_value, new_value=_as_dict(obj))
    _commit_or_409(db)
    return {"message": f"{entity_type} activated", "id": obj_id}


@router.get("/bootstrap")
def bootstrap(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    scoped_station_ids = get_accessible_station_ids(db, user)
    scoped_contract_ids = get_accessible_contract_ids(db, user)
    scoped_user_ids = get_scope_user_ids(db, user, include_self=True)

    station_query = db.query(Station).order_by(Station.station_name)
    contract_query = db.query(Contract).order_by(Contract.contract_code)
    contract_station_query = db.query(ContractStation).filter(ContractStation.is_active == True)  # noqa: E712
    user_query = db.query(User).options(joinedload(User.role)).filter(User.is_active == True).order_by(User.name)  # noqa: E712

    if scoped_station_ids is not None:
        station_query = station_query.filter(Station.id.in_(scoped_station_ids) if scoped_station_ids else False)
        contract_station_query = contract_station_query.filter(ContractStation.station_id.in_(scoped_station_ids) if scoped_station_ids else False)
    if scoped_contract_ids is not None:
        contract_query = contract_query.filter(Contract.id.in_(scoped_contract_ids) if scoped_contract_ids else False)
        contract_station_query = contract_station_query.filter(ContractStation.contract_id.in_(scoped_contract_ids) if scoped_contract_ids else False)
    if scoped_user_ids is not None and not is_admin_scope(user):
        user_query = user_query.filter(User.id.in_(scoped_user_ids) if scoped_user_ids else False)

    return {
        "can_manage_master": _can_manage(user),
        "current_role": user.role.code.value if user.role else None,
        "lines": db.query(Line).order_by(Line.line_code).all(),
        "stations": station_query.all(),
        "contracts": contract_query.all(),
        "contractors": db.query(Contractor).order_by(Contractor.contractor_name).all(),
        "grading_schemes": db.query(GradingScheme).order_by(GradingScheme.name).all(),
        "grading_options": db.query(GradingOption).order_by(GradingOption.scheme_id, GradingOption.sort_order).all(),
        "inspection_attributes": db.query(InspectionAttribute).order_by(InspectionAttribute.sort_order).all(),
        "inspection_sub_areas": db.query(InspectionSubArea).order_by(InspectionSubArea.attribute_id, InspectionSubArea.sort_order).all(),
        "billing_cycles": db.query(BillingCycle).order_by(BillingCycle.start_date.desc()).all(),
        "contract_stations": contract_station_query.all(),
        "users": [_safe_user(u) for u in user_query.all()],
    }


@router.get("/lines", response_model=list[LineOut])
def list_lines(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Line).order_by(Line.line_code).all()


@router.post("/lines", response_model=LineOut)
def create_line(payload: LineCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _create(db, user, Line, payload, "LINE")


@router.put("/lines/{line_id}", response_model=LineOut)
def update_line(line_id: int, payload: LineUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _update(db, user, Line, line_id, payload, "LINE")


@router.delete("/lines/{line_id}")
def deactivate_line(line_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, Line, line_id, "LINE")


@router.put("/lines/{line_id}/activate")
def activate_line(line_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, Line, line_id, "LINE")


@router.get("/contractors", response_model=list[ContractorOut])
def list_contractors(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Contractor).order_by(Contractor.contractor_name).all()


@router.post("/contractors", response_model=ContractorOut)
def create_contractor(payload: ContractorCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _create(db, user, Contractor, payload, "CONTRACTOR")


@router.put("/contractors/{contractor_id}", response_model=ContractorOut)
def update_contractor(contractor_id: int, payload: ContractorUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _update(db, user, Contractor, contractor_id, payload, "CONTRACTOR")


@router.delete("/contractors/{contractor_id}")
def deactivate_contractor(contractor_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, Contractor, contractor_id, "CONTRACTOR")


@router.put("/contractors/{contractor_id}/activate")
def activate_contractor(contractor_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, Contractor, contractor_id, "CONTRACTOR")


@router.get("/stations", response_model=list[StationOut])
def list_stations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    station_ids = get_accessible_station_ids(db, user)
    query = db.query(Station).order_by(Station.station_name)
    if station_ids is not None:
        query = query.filter(Station.id.in_(station_ids) if station_ids else False)
    return query.all()


@router.post("/stations", response_model=StationOut)
def create_station(payload: StationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_or_404(db, Line, payload.line_id)
    return _create(db, user, Station, payload, "STATION")


@router.put("/stations/{station_id}", response_model=StationOut)
def update_station(station_id: int, payload: StationUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.line_id:
        _get_or_404(db, Line, payload.line_id)
    return _update(db, user, Station, station_id, payload, "STATION")


@router.delete("/stations/{station_id}")
def deactivate_station(station_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, Station, station_id, "STATION")


@router.put("/stations/{station_id}/activate")
def activate_station(station_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, Station, station_id, "STATION")


@router.get("/contracts", response_model=list[ContractOut])
def list_contracts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    contract_ids = get_accessible_contract_ids(db, user)
    query = db.query(Contract).order_by(Contract.contract_code)
    if contract_ids is not None:
        query = query.filter(Contract.id.in_(contract_ids) if contract_ids else False)
    return query.all()


@router.post("/contracts", response_model=ContractOut)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="Contract end date cannot be before start date")
    _get_or_404(db, Contractor, payload.contractor_id)
    _get_or_404(db, GradingScheme, payload.grading_scheme_id)
    return _create(db, user, Contract, payload, "CONTRACT")


@router.put("/contracts/{contract_id}", response_model=ContractOut)
def update_contract(contract_id: int, payload: ContractUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.contractor_id:
        _get_or_404(db, Contractor, payload.contractor_id)
    if payload.grading_scheme_id:
        _get_or_404(db, GradingScheme, payload.grading_scheme_id)
    return _update(db, user, Contract, contract_id, payload, "CONTRACT")


@router.delete("/contracts/{contract_id}")
def deactivate_contract(contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, Contract, contract_id, "CONTRACT")


@router.put("/contracts/{contract_id}/activate")
def activate_contract(contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, Contract, contract_id, "CONTRACT")


@router.get("/contracts/{contract_id}/stations", response_model=list[ContractStationOut])
def list_contract_stations(contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_or_404(db, Contract, contract_id)
    return db.query(ContractStation).filter_by(contract_id=contract_id, is_active=True).all()


@router.post("/contracts/{contract_id}/stations", response_model=ContractStationOut)
def add_contract_station(contract_id: int, payload: ContractStationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    _get_or_404(db, Contract, contract_id)
    _get_or_404(db, Station, payload.station_id)
    mapping = db.query(ContractStation).filter_by(contract_id=contract_id, station_id=payload.station_id).first()
    if mapping:
        mapping.is_active = True
    else:
        mapping = ContractStation(contract_id=contract_id, station_id=payload.station_id)
        db.add(mapping)
    db.flush()
    audit_log(db, actor=user, action="MASTER_CONTRACT_STATION_MAPPED", entity_type="CONTRACT_STATION", entity_id=mapping.id, new_value=_as_dict(mapping))
    _commit_or_409(db)
    db.refresh(mapping)
    return mapping


@router.delete("/contracts/{contract_id}/stations/{station_id}")
def remove_contract_station(contract_id: int, station_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    mapping = db.query(ContractStation).filter_by(contract_id=contract_id, station_id=station_id, is_active=True).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Contract-station mapping not found")
    old_value = _as_dict(mapping)
    mapping.is_active = False
    db.flush()
    audit_log(db, actor=user, action="MASTER_CONTRACT_STATION_UNMAPPED", entity_type="CONTRACT_STATION", entity_id=mapping.id, old_value=old_value, new_value=_as_dict(mapping))
    _commit_or_409(db)
    return {"message": "Station removed from contract", "contract_id": contract_id, "station_id": station_id}


@router.get("/inspection-attributes", response_model=list[InspectionAttributeOut])
def list_inspection_attributes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(InspectionAttribute).order_by(InspectionAttribute.sort_order).all()


@router.post("/inspection-attributes", response_model=InspectionAttributeOut)
def create_inspection_attribute(payload: InspectionAttributeCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _create(db, user, InspectionAttribute, payload, "INSPECTION_ATTRIBUTE")


@router.put("/inspection-attributes/{attribute_id}", response_model=InspectionAttributeOut)
def update_inspection_attribute(attribute_id: int, payload: InspectionAttributeUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _update(db, user, InspectionAttribute, attribute_id, payload, "INSPECTION_ATTRIBUTE")


@router.delete("/inspection-attributes/{attribute_id}")
def deactivate_inspection_attribute(attribute_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, InspectionAttribute, attribute_id, "INSPECTION_ATTRIBUTE")


@router.put("/inspection-attributes/{attribute_id}/activate")
def activate_inspection_attribute(attribute_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, InspectionAttribute, attribute_id, "INSPECTION_ATTRIBUTE")


@router.get("/inspection-attributes/{attribute_id}/sub-areas", response_model=list[InspectionSubAreaOut])
def list_sub_areas_by_attribute(attribute_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_or_404(db, InspectionAttribute, attribute_id)
    return db.query(InspectionSubArea).filter_by(attribute_id=attribute_id, is_active=True).order_by(InspectionSubArea.sort_order).all()


@router.get("/inspection-sub-areas", response_model=list[InspectionSubAreaOut])
def list_inspection_sub_areas(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(InspectionSubArea).order_by(InspectionSubArea.attribute_id, InspectionSubArea.sort_order).all()


@router.post("/inspection-sub-areas", response_model=InspectionSubAreaOut)
def create_inspection_sub_area(payload: InspectionSubAreaCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_or_404(db, InspectionAttribute, payload.attribute_id)
    return _create(db, user, InspectionSubArea, payload, "INSPECTION_SUB_AREA")


@router.put("/inspection-sub-areas/{sub_area_id}", response_model=InspectionSubAreaOut)
def update_inspection_sub_area(sub_area_id: int, payload: InspectionSubAreaUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.attribute_id:
        _get_or_404(db, InspectionAttribute, payload.attribute_id)
    return _update(db, user, InspectionSubArea, sub_area_id, payload, "INSPECTION_SUB_AREA")


@router.delete("/inspection-sub-areas/{sub_area_id}")
def deactivate_inspection_sub_area(sub_area_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, InspectionSubArea, sub_area_id, "INSPECTION_SUB_AREA")


@router.put("/inspection-sub-areas/{sub_area_id}/activate")
def activate_inspection_sub_area(sub_area_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, InspectionSubArea, sub_area_id, "INSPECTION_SUB_AREA")


@router.get("/grading-schemes", response_model=list[GradingSchemeOut])
def list_grading_schemes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(GradingScheme).order_by(GradingScheme.name).all()


@router.post("/grading-schemes", response_model=GradingSchemeOut)
def create_grading_scheme(payload: GradingSchemeCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _create(db, user, GradingScheme, payload, "GRADING_SCHEME")


@router.put("/grading-schemes/{scheme_id}", response_model=GradingSchemeOut)
def update_grading_scheme(scheme_id: int, payload: GradingSchemeUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _update(db, user, GradingScheme, scheme_id, payload, "GRADING_SCHEME")


@router.delete("/grading-schemes/{scheme_id}")
def deactivate_grading_scheme(scheme_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, GradingScheme, scheme_id, "GRADING_SCHEME")


@router.put("/grading-schemes/{scheme_id}/activate")
def activate_grading_scheme(scheme_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, GradingScheme, scheme_id, "GRADING_SCHEME")


@router.get("/grading-options", response_model=list[GradingOptionOut])
def list_grading_options(scheme_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(GradingOption)
    if scheme_id:
        q = q.filter_by(scheme_id=scheme_id)
    return q.order_by(GradingOption.scheme_id, GradingOption.sort_order).all()


@router.post("/grading-options", response_model=GradingOptionOut)
def create_grading_option(payload: GradingOptionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_or_404(db, GradingScheme, payload.scheme_id)
    return _create(db, user, GradingOption, payload, "GRADING_OPTION")


@router.put("/grading-options/{option_id}", response_model=GradingOptionOut)
def update_grading_option(option_id: int, payload: GradingOptionUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.scheme_id:
        _get_or_404(db, GradingScheme, payload.scheme_id)
    return _update(db, user, GradingOption, option_id, payload, "GRADING_OPTION")


@router.delete("/grading-options/{option_id}")
def delete_grading_option(option_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_manage(user)
    obj = _get_or_404(db, GradingOption, option_id)
    old_value = _as_dict(obj)
    db.delete(obj)
    audit_log(db, actor=user, action="MASTER_GRADING_OPTION_DELETED", entity_type="GRADING_OPTION", entity_id=option_id, old_value=old_value)
    _commit_or_409(db)
    return {"message": "Grading option deleted", "id": option_id}
