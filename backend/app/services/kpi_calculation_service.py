from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.all_models import (
    BillingCycle,
    Contract,
    ContractStation,
    Inspection,
    InspectionAttributeScore,
    InspectionEntry,
    InspectionStatus,
    InspectionType,
    MonthlyBillValue,
    MonthlyContractScore,
    MonthlyStationScore,
    PenaltyCalculation,
)


# In this application DGM_APPROVED is the terminal "Final approved by GM/Ops"
# status kept for compatibility with older table values. CLOSED is accepted for
# future/archived approved records if the project starts closing approved cases.
KPI_APPROVED_STATUSES = (
    InspectionStatus.DGM_APPROVED,
    InspectionStatus.CLOSED,
)

# These are final decisions by GM/Ops. Rejected inspections do not contribute to
# KPI score, but they should not keep the month in a "pending approval" state.
GM_FINAL_DECISION_STATUSES = (
    InspectionStatus.DGM_APPROVED,
    InspectionStatus.DGM_REJECTED,
    InspectionStatus.CLOSED,
)

UNSUBMITTED_STATUSES = (
    InspectionStatus.DRAFT,
    InspectionStatus.RETURNED_FOR_CLARIFICATION,
)


def _cycle_contract_inspections(db: Session, contract_id: int, cycle: BillingCycle):
    return db.query(Inspection).filter(
        Inspection.contract_id == contract_id,
        Inspection.inspection_date >= cycle.start_date,
        Inspection.inspection_date <= cycle.end_date,
    )


def _pending_gm_decision_count(db: Session, contract_id: int, cycle: BillingCycle) -> int:
    """Count submitted inspections in the month that have not reached GM/Ops final decision.

    Draft and returned inspections are not submitted monthly KPI evidence yet, so they are
    ignored. Anything already submitted to LM/DGM/GM but not finally approved/rejected blocks
    penalty generation for the month.
    """

    return (
        _cycle_contract_inspections(db, contract_id, cycle)
        .filter(~Inspection.status.in_(list(GM_FINAL_DECISION_STATUSES)))
        .filter(~Inspection.status.in_(list(UNSUBMITTED_STATUSES)))
        .count()
    )


def _approved_inspection_count(db: Session, contract_id: int, cycle: BillingCycle) -> int:
    return (
        _cycle_contract_inspections(db, contract_id, cycle)
        .filter(Inspection.status.in_(list(KPI_APPROVED_STATUSES)))
        .count()
    )


def _inspection_score(db: Session, inspection_id: int) -> float:
    """Return an inspection score from the current entry-based UI, with legacy fallback."""

    entry_avg = (
        db.query(func.avg(InspectionEntry.grade_percentage))
        .filter(
            InspectionEntry.inspection_id == inspection_id,
            InspectionEntry.is_deleted.is_(False),
        )
        .scalar()
    )
    if entry_avg is not None:
        return float(entry_avg or 0)

    legacy_avg = (
        db.query(func.avg(InspectionAttributeScore.grade_percentage))
        .filter(InspectionAttributeScore.inspection_id == inspection_id)
        .scalar()
    )
    return float(legacy_avg or 0)


def _average_for_type(
    db: Session,
    contract_id: int,
    station_id: int,
    cycle: BillingCycle,
    inspection_type: InspectionType,
) -> tuple[float, int]:
    inspections = (
        db.query(Inspection)
        .filter(
            Inspection.contract_id == contract_id,
            Inspection.station_id == station_id,
            Inspection.inspection_type == inspection_type,
            Inspection.inspection_date >= cycle.start_date,
            Inspection.inspection_date <= cycle.end_date,
            Inspection.status.in_(list(KPI_APPROVED_STATUSES)),
        )
        .all()
    )
    if not inspections:
        return 0.0, 0
    scores = [_inspection_score(db, i.id) for i in inspections]
    return round(sum(scores) / len(scores), 2), len(scores)


def calculate_monthly_kpi6(db: Session, billing_cycle_id: int, contract_id: int) -> dict:
    cycle = db.get(BillingCycle, billing_cycle_id)
    contract = db.get(Contract, contract_id)
    if not cycle or not contract:
        raise HTTPException(status_code=404, detail="Invalid billing cycle or contract")

    pending_count = _pending_gm_decision_count(db, contract_id, cycle)
    if pending_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"KPI-6 monthly penalty cannot be calculated yet. "
                f"{pending_count} submitted inspection(s) for {cycle.name or cycle.code} "
                f"are still pending final GM/Ops decision."
            ),
        )

    approved_count = _approved_inspection_count(db, contract_id, cycle)
    if approved_count <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No GM/Ops-approved inspection is available for {cycle.name or cycle.code}. "
                "Monthly KPI penalty is calculated only from inspections finally approved by GM/Ops."
            ),
        )

    mappings = db.query(ContractStation).filter_by(contract_id=contract_id, is_active=True).all()
    now = datetime.utcnow()
    station_scores = []

    for mapping in mappings:
        sm_avg, sm_count = _average_for_type(db, contract_id, mapping.station_id, cycle, InspectionType.SM_INSPECTION)
        eit_avg, eit_count = _average_for_type(db, contract_id, mapping.station_id, cycle, InspectionType.EIT_INSPECTION)
        final_score = round((sm_avg * settings.KPI6_SM_WEIGHT) + (eit_avg * settings.KPI6_EIT_WEIGHT), 2)

        row = (
            db.query(MonthlyStationScore)
            .filter_by(
                billing_cycle_id=billing_cycle_id,
                contract_id=contract_id,
                station_id=mapping.station_id,
            )
            .first()
        )
        if not row:
            row = MonthlyStationScore(
                billing_cycle_id=billing_cycle_id,
                contract_id=contract_id,
                station_id=mapping.station_id,
            )
            db.add(row)

        row.sm_inspection_count = sm_count
        row.eit_inspection_count = eit_count
        row.sm_average_score = sm_avg
        row.eit_average_score = eit_avg
        row.final_station_score = final_score
        row.calculated_at = now
        station_scores.append(final_score)

    average_score = round(sum(station_scores) / len(station_scores), 2) if station_scores else 0
    is_penalty = average_score < contract.kpi6_threshold_percent

    contract_score = (
        db.query(MonthlyContractScore)
        .filter_by(billing_cycle_id=billing_cycle_id, contract_id=contract_id)
        .first()
    )
    if not contract_score:
        contract_score = MonthlyContractScore(billing_cycle_id=billing_cycle_id, contract_id=contract_id)
        db.add(contract_score)

    contract_score.station_count = len(station_scores)
    contract_score.average_score = average_score
    contract_score.is_penalty_applicable = is_penalty
    contract_score.calculated_at = now

    bill = db.query(MonthlyBillValue).filter_by(billing_cycle_id=billing_cycle_id, contract_id=contract_id).first()
    monthly_bill = bill.bill_value if bill else contract.monthly_bill_value_default
    penalty_amount = round((monthly_bill * contract.kpi6_penalty_percent / 100), 2) if is_penalty else 0.0

    penalty = (
        db.query(PenaltyCalculation)
        .filter_by(billing_cycle_id=billing_cycle_id, contract_id=contract_id, kpi_code="KPI6")
        .first()
    )
    if not penalty:
        penalty = PenaltyCalculation(billing_cycle_id=billing_cycle_id, contract_id=contract_id, kpi_code="KPI6")
        db.add(penalty)

    penalty.monthly_bill_value = monthly_bill
    penalty.kpi_score = average_score
    penalty.threshold_percentage = contract.kpi6_threshold_percent
    penalty.penalty_percentage = contract.kpi6_penalty_percent
    penalty.penalty_amount = penalty_amount
    penalty.status = "GENERATED_AFTER_GM_APPROVAL"

    db.commit()
    return {
        "contract_id": contract_id,
        "billing_cycle_id": billing_cycle_id,
        "average_score": average_score,
        "is_penalty_applicable": is_penalty,
        "penalty_amount": penalty_amount,
        "approved_inspection_count": approved_count,
        "pending_gm_decision_count": pending_count,
    }
