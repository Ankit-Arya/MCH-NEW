from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.models.all_models import MonthlyContractScore, MonthlyStationScore, PenaltyCalculation, RoleCode, User
from app.schemas.kpi import MonthlyCalculationRequest, MonthlyCalculationResponse
from app.services.kpi_calculation_service import calculate_monthly_kpi6

router = APIRouter()


@router.post("/calculate/monthly", response_model=MonthlyCalculationResponse)
def calculate_monthly(payload: MonthlyCalculationRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN, RoleCode.DGM_HK, RoleCode.GM_OPS})
    return calculate_monthly_kpi6(db, payload.billing_cycle_id, payload.contract_id)


@router.get("/station-scores")
def station_scores(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(MonthlyStationScore).order_by(MonthlyStationScore.calculated_at.desc()).limit(500).all()


@router.get("/contract-scores")
def contract_scores(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(MonthlyContractScore).order_by(MonthlyContractScore.calculated_at.desc()).limit(200).all()


@router.get("/penalties")
def penalties(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(PenaltyCalculation).order_by(PenaltyCalculation.created_at.desc()).limit(200).all()
