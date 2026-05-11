from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.config import settings
from app.models.all_models import (
    BillingCycle,
    Contract,
    ContractStation,
    Inspection,
    InspectionAttributeScore,
    InspectionStatus,
    InspectionType,
    MonthlyBillValue,
    MonthlyContractScore,
    MonthlyStationScore,
    PenaltyCalculation,
)


def _inspection_score(db: Session, inspection_id: int) -> float:
    avg = db.query(func.avg(InspectionAttributeScore.grade_percentage)).filter(InspectionAttributeScore.inspection_id == inspection_id).scalar()
    return float(avg or 0)


def _average_for_type(db: Session, contract_id: int, station_id: int, cycle: BillingCycle, inspection_type: InspectionType) -> tuple[float, int]:
    inspections = db.query(Inspection).filter(
        Inspection.contract_id == contract_id,
        Inspection.station_id == station_id,
        Inspection.inspection_type == inspection_type,
        Inspection.inspection_date >= cycle.start_date,
        Inspection.inspection_date <= cycle.end_date,
        Inspection.status.in_([
            InspectionStatus.UNDER_LINE_MANAGER_REVIEW,
            InspectionStatus.LINE_MANAGER_RECOMMENDED,
            InspectionStatus.DGM_APPROVED,
            InspectionStatus.GM_REVIEW_REQUIRED,
            InspectionStatus.GM_REVIEWED,
            InspectionStatus.CLOSED,
        ]),
    ).all()
    if not inspections:
        return 0.0, 0
    scores = [_inspection_score(db, i.id) for i in inspections]
    return round(sum(scores) / len(scores), 2), len(scores)


def calculate_monthly_kpi6(db: Session, billing_cycle_id: int, contract_id: int) -> dict:
    cycle = db.get(BillingCycle, billing_cycle_id)
    contract = db.get(Contract, contract_id)
    if not cycle or not contract:
        raise ValueError("Invalid billing cycle or contract")

    mappings = db.query(ContractStation).filter_by(contract_id=contract_id, is_active=True).all()
    station_scores = []
    for mapping in mappings:
        sm_avg, sm_count = _average_for_type(db, contract_id, mapping.station_id, cycle, InspectionType.SM_INSPECTION)
        eit_avg, eit_count = _average_for_type(db, contract_id, mapping.station_id, cycle, InspectionType.EIT_INSPECTION)
        final_score = round((sm_avg * settings.KPI6_SM_WEIGHT) + (eit_avg * settings.KPI6_EIT_WEIGHT), 2)
        row = db.query(MonthlyStationScore).filter_by(billing_cycle_id=billing_cycle_id, contract_id=contract_id, station_id=mapping.station_id).first()
        if not row:
            row = MonthlyStationScore(billing_cycle_id=billing_cycle_id, contract_id=contract_id, station_id=mapping.station_id)
            db.add(row)
        row.sm_inspection_count = sm_count
        row.eit_inspection_count = eit_count
        row.sm_average_score = sm_avg
        row.eit_average_score = eit_avg
        row.final_station_score = final_score
        station_scores.append(final_score)

    average_score = round(sum(station_scores) / len(station_scores), 2) if station_scores else 0
    is_penalty = average_score < contract.kpi6_threshold_percent

    contract_score = db.query(MonthlyContractScore).filter_by(billing_cycle_id=billing_cycle_id, contract_id=contract_id).first()
    if not contract_score:
        contract_score = MonthlyContractScore(billing_cycle_id=billing_cycle_id, contract_id=contract_id)
        db.add(contract_score)
    contract_score.station_count = len(station_scores)
    contract_score.average_score = average_score
    contract_score.is_penalty_applicable = is_penalty

    bill = db.query(MonthlyBillValue).filter_by(billing_cycle_id=billing_cycle_id, contract_id=contract_id).first()
    monthly_bill = bill.bill_value if bill else contract.monthly_bill_value_default
    penalty_amount = round((monthly_bill * contract.kpi6_penalty_percent / 100), 2) if is_penalty else 0.0

    penalty = db.query(PenaltyCalculation).filter_by(billing_cycle_id=billing_cycle_id, contract_id=contract_id, kpi_code="KPI6").first()
    if not penalty:
        penalty = PenaltyCalculation(billing_cycle_id=billing_cycle_id, contract_id=contract_id, kpi_code="KPI6")
        db.add(penalty)
    penalty.monthly_bill_value = monthly_bill
    penalty.kpi_score = average_score
    penalty.threshold_percentage = contract.kpi6_threshold_percent
    penalty.penalty_percentage = contract.kpi6_penalty_percent
    penalty.penalty_amount = penalty_amount
    penalty.status = "GENERATED"

    db.commit()
    return {
        "contract_id": contract_id,
        "billing_cycle_id": billing_cycle_id,
        "average_score": average_score,
        "is_penalty_applicable": is_penalty,
        "penalty_amount": penalty_amount,
    }
