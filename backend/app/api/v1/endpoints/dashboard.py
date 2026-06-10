
from collections import defaultdict
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import apply_contract_scope, apply_inspection_scope, apply_review_scope, apply_station_scope, get_accessible_contract_ids, get_accessible_station_ids, is_admin_scope
from app.models.all_models import (
    Contract,
    Inspection,
    InspectionAttributeScore,
    InspectionStatus,
    MonthlyContractScore,
    PenaltyCalculation,
    Station,
    User,
)

router = APIRouter()

PENDING = [InspectionStatus.UNDER_LINE_MANAGER_REVIEW, InspectionStatus.LINE_MANAGER_RECOMMENDED, InspectionStatus.GM_REVIEW_REQUIRED]


def _label_for(d: date, period: str) -> str:
    if period == "weekly":
        iso = d.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if period == "yearly":
        return str(d.year)
    return f"{d.year}-{d.month:02d}"


def _score_for(inspection: Inspection) -> float:
    if not inspection.attribute_scores:
        return 0.0
    return round(sum(s.grade_percentage for s in inspection.attribute_scores) / len(inspection.attribute_scores), 2)


def _filtered_inspections(db: Session, user: User, from_date=None, to_date=None, station_id=None, contract_id=None):
    q = apply_inspection_scope(db.query(Inspection), db, user)
    if from_date:
        q = q.filter(Inspection.inspection_date >= from_date)
    if to_date:
        q = q.filter(Inspection.inspection_date <= to_date)
    if station_id:
        q = q.filter(Inspection.station_id == station_id)
    if contract_id:
        q = q.filter(Inspection.contract_id == contract_id)
    return q


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection_query = apply_inspection_scope(db.query(Inspection), db, user)
    station_query = db.query(Station)
    contract_query = db.query(Contract)
    penalty_query = db.query(PenaltyCalculation)
    contract_score_query = db.query(MonthlyContractScore)

    if not is_admin_scope(user):
        station_query = apply_station_scope(station_query, Station.id, db, user)
        contract_query = apply_contract_scope(contract_query, Contract.id, db, user)
        penalty_query = apply_contract_scope(penalty_query, PenaltyCalculation.contract_id, db, user)
        contract_score_query = apply_contract_scope(contract_score_query, MonthlyContractScore.contract_id, db, user)

    penalty_amount = penalty_query.with_entities(func.coalesce(func.sum(PenaltyCalculation.penalty_amount), 0)).scalar() or 0
    latest_score = contract_score_query.order_by(MonthlyContractScore.calculated_at.desc()).first()
    return {
        "contracts": contract_query.with_entities(func.count(Contract.id)).scalar() or 0,
        "stations": station_query.with_entities(func.count(Station.id)).scalar() or 0,
        "inspections": inspection_query.with_entities(func.count(Inspection.id)).scalar() or 0,
        "pending_reviews": apply_review_scope(db.query(Inspection), db, user).with_entities(func.count(Inspection.id)).scalar() or 0,
        "generated_penalties": penalty_query.with_entities(func.count(PenaltyCalculation.id)).scalar() or 0,
        "penalty_amount": float(penalty_amount),
        "latest_score": float(latest_score.average_score) if latest_score else 0,
    }


@router.get("/analytics")
def analytics(
    period: str = Query("monthly", pattern="^(weekly|monthly|yearly)$"),
    from_date: date | None = None,
    to_date: date | None = None,
    station_id: int | None = None,
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inspections = _filtered_inspections(db, user, from_date, to_date, station_id, contract_id).order_by(Inspection.inspection_date).all()
    penalty_query = db.query(PenaltyCalculation)
    if not is_admin_scope(user):
        penalty_query = apply_contract_scope(penalty_query, PenaltyCalculation.contract_id, db, user)
    if contract_id:
        penalty_query = penalty_query.filter(PenaltyCalculation.contract_id == contract_id)
    penalties = penalty_query.all()

    score_buckets = defaultdict(list)
    volume = defaultdict(int)
    station_scores = defaultdict(list)
    grade_dist = defaultdict(int)
    status_dist = defaultdict(int)

    for ins in inspections:
        label = _label_for(ins.inspection_date, period)
        score = _score_for(ins)
        score_buckets[label].append(score)
        volume[label] += 1
        station_scores[ins.station.station_name if ins.station else f"Station {ins.station_id}"].append(score)
        status_dist[ins.status.value] += 1
        for s in ins.attribute_scores:
            grade_dist[s.grade_code] += 1

    score_trend = [{"label": k, "value": round(sum(v) / len(v), 2)} for k, v in sorted(score_buckets.items())]
    inspection_volume = [{"label": k, "value": v} for k, v in sorted(volume.items())]
    station_score_rows = [{"label": k, "value": round(sum(v) / len(v), 2)} for k, v in station_scores.items()]
    station_score_rows.sort(key=lambda x: x["value"])
    grade_distribution = [{"label": g, "value": grade_dist.get(g, 0)} for g in ["A", "B", "C", "D", "E", "F"]]
    status_distribution = [{"label": k, "value": v} for k, v in status_dist.items()]

    pending_reviews = sum(v for k, v in status_dist.items() if k in [p.value for p in PENDING])
    penalty_amount = sum(float(p.penalty_amount or 0) for p in penalties)
    latest_score = score_trend[-1]["value"] if score_trend else 0

    return {
        "summary": {
            "contracts": (apply_contract_scope(db.query(Contract), Contract.id, db, user) if not is_admin_scope(user) else db.query(Contract)).with_entities(func.count(Contract.id)).scalar() or 0,
            "stations": (apply_station_scope(db.query(Station), Station.id, db, user) if not is_admin_scope(user) else db.query(Station)).with_entities(func.count(Station.id)).scalar() or 0,
            "inspections": len(inspections),
            "pending_reviews": pending_reviews,
            "generated_penalties": len(penalties),
            "penalty_amount": penalty_amount,
            "latest_score": latest_score,
        },
        "score_trend": score_trend,
        "inspection_volume": inspection_volume,
        "station_scores": station_score_rows[:12],
        "grade_distribution": grade_distribution,
        "status_distribution": status_distribution,
        "contract_scores": [
            {"label": f"Contract {s.contract_id}/Cycle {s.billing_cycle_id}", "value": s.average_score, "penalty": s.is_penalty_applicable}
            for s in (apply_contract_scope(db.query(MonthlyContractScore), MonthlyContractScore.contract_id, db, user) if not is_admin_scope(user) else db.query(MonthlyContractScore)).order_by(MonthlyContractScore.calculated_at.desc()).limit(12).all()
        ],
        "role_view": user.role.code.value,
    }


@router.get("/contract-wise-score")
def contract_wise_score(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(MonthlyContractScore)
    if not is_admin_scope(user):
        query = apply_contract_scope(query, MonthlyContractScore.contract_id, db, user)
    return query.order_by(MonthlyContractScore.calculated_at.desc()).limit(50).all()


@router.get("/pending-reviews")
def pending_reviews(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return apply_review_scope(db.query(Inspection), db, user).limit(50).all()
