
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.models.all_models import (
    BillingCycle,
    Contract,
    Contractor,
    GradingScheme,
    InspectionAttribute,
    Line,
    RoleCode,
    Station,
    User,
)
from app.schemas.master import StationCreate, StationOut, ContractCreate, ContractOut

router = APIRouter()


def _safe_user(u: User) -> dict:
    return {"id": u.id, "username": u.username, "name": u.name, "emp_number": u.emp_number, "role": u.role.code.value if u.role else None}


@router.get("/bootstrap")
def bootstrap(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    users = db.query(User).filter(User.is_active == True).order_by(User.name).all()  # noqa: E712
    return {
        "lines": db.query(Line).filter_by(is_active=True).all(),
        "stations": db.query(Station).filter_by(is_active=True).order_by(Station.station_name).all(),
        "contracts": db.query(Contract).filter_by(is_active=True).order_by(Contract.contract_code).all(),
        "contractors": db.query(Contractor).filter_by(is_active=True).all(),
        "grading_schemes": db.query(GradingScheme).filter_by(is_active=True).all(),
        "inspection_attributes": db.query(InspectionAttribute).filter_by(is_active=True).order_by(InspectionAttribute.sort_order).all(),
        "billing_cycles": db.query(BillingCycle).order_by(BillingCycle.start_date.desc()).all(),
        "users": [_safe_user(u) for u in users],
    }


@router.get("/stations", response_model=list[StationOut])
def stations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Station).filter_by(is_active=True).order_by(Station.station_name).all()


@router.post("/stations", response_model=StationOut)
def create_station(payload: StationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN})
    station = Station(**payload.model_dump())
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@router.get("/contracts", response_model=list[ContractOut])
def contracts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Contract).filter_by(is_active=True).order_by(Contract.contract_code).all()


@router.post("/contracts", response_model=ContractOut)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN})
    contract = Contract(**payload.model_dump())
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/inspection-attributes")
def inspection_attributes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(InspectionAttribute).filter_by(is_active=True).order_by(InspectionAttribute.sort_order).all()


@router.get("/grading-schemes")
def grading_schemes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(GradingScheme).filter_by(is_active=True).all()
