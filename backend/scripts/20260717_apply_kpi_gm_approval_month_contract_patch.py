from __future__ import print_function

from pathlib import Path


def find_project_root():
    candidates = [Path.cwd().resolve()]
    try:
        here = Path(__file__).resolve()
        candidates.extend([parent for parent in here.parents])
    except Exception:
        pass

    seen = set()
    for base in candidates:
        if str(base) in seen:
            continue
        seen.add(str(base))
        if (base / "backend" / "app" / "api" / "v1" / "endpoints" / "kpi.py").exists():
            return base
        if (base / "app" / "api" / "v1" / "endpoints" / "kpi.py").exists() and base.name == "backend":
            return base.parent

    raise RuntimeError("Could not find project root. Run this script from mch-inspection-platform root or copy it under backend\\scripts.")


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


KPI_SERVICE = r'''
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
'''

KPI_ENDPOINT = r'''
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import apply_contract_scope, apply_station_scope, is_admin_scope, require_roles
from app.models.all_models import MonthlyContractScore, MonthlyStationScore, PenaltyCalculation, RoleCode, User
from app.schemas.kpi import MonthlyCalculationRequest, MonthlyCalculationResponse
from app.services.kpi_calculation_service import calculate_monthly_kpi6

router = APIRouter()


@router.post("/calculate/monthly", response_model=MonthlyCalculationResponse)
def calculate_monthly(payload: MonthlyCalculationRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN, RoleCode.DGM_HK, RoleCode.GM_OPS})
    return calculate_monthly_kpi6(db, payload.billing_cycle_id, payload.contract_id)


@router.get("/station-scores")
def station_scores(
    billing_cycle_id: int | None = None,
    contract_id: int | None = None,
    station_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(MonthlyStationScore)
    if not is_admin_scope(user):
        query = apply_station_scope(query, MonthlyStationScore.station_id, db, user)
    if billing_cycle_id:
        query = query.filter(MonthlyStationScore.billing_cycle_id == billing_cycle_id)
    if contract_id:
        query = query.filter(MonthlyStationScore.contract_id == contract_id)
    if station_id:
        query = query.filter(MonthlyStationScore.station_id == station_id)
    return query.order_by(MonthlyStationScore.calculated_at.desc()).limit(500).all()


@router.get("/contract-scores")
def contract_scores(
    billing_cycle_id: int | None = None,
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(MonthlyContractScore)
    if not is_admin_scope(user):
        query = apply_contract_scope(query, MonthlyContractScore.contract_id, db, user)
    if billing_cycle_id:
        query = query.filter(MonthlyContractScore.billing_cycle_id == billing_cycle_id)
    if contract_id:
        query = query.filter(MonthlyContractScore.contract_id == contract_id)
    return query.order_by(MonthlyContractScore.calculated_at.desc()).limit(200).all()


@router.get("/penalties")
def penalties(
    billing_cycle_id: int | None = None,
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(PenaltyCalculation)
    if not is_admin_scope(user):
        query = apply_contract_scope(query, PenaltyCalculation.contract_id, db, user)
    if billing_cycle_id:
        query = query.filter(PenaltyCalculation.billing_cycle_id == billing_cycle_id)
    if contract_id:
        query = query.filter(PenaltyCalculation.contract_id == contract_id)
    return query.order_by(PenaltyCalculation.created_at.desc()).limit(200).all()
'''

KPI_SCHEMA = r'''
from pydantic import BaseModel


class MonthlyCalculationRequest(BaseModel):
    billing_cycle_id: int
    contract_id: int


class MonthlyCalculationResponse(BaseModel):
    contract_id: int
    billing_cycle_id: int
    average_score: float
    is_penalty_applicable: bool
    penalty_amount: float
    approved_inspection_count: int = 0
    pending_gm_decision_count: int = 0
'''

DASHBOARD_ENDPOINT = r'''
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import apply_contract_scope, apply_inspection_scope, apply_review_scope, apply_station_scope, is_admin_scope
from app.models.all_models import (
    BillingCycle,
    Contract,
    Inspection,
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
    active_entries = [e for e in getattr(inspection, "entries", []) if not getattr(e, "is_deleted", False)]
    if active_entries:
        return round(sum(e.grade_percentage or 0 for e in active_entries) / len(active_entries), 2)
    if inspection.attribute_scores:
        return round(sum(s.grade_percentage for s in inspection.attribute_scores) / len(inspection.attribute_scores), 2)
    return 0.0


def _apply_cycle_dates(db: Session, billing_cycle_id: int | None, from_date=None, to_date=None):
    if not billing_cycle_id:
        return from_date, to_date, None
    cycle = db.get(BillingCycle, billing_cycle_id)
    if not cycle:
        return from_date, to_date, None
    return cycle.start_date, cycle.end_date, cycle


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
def summary(
    billing_cycle_id: int | None = None,
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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

    if billing_cycle_id:
        penalty_query = penalty_query.filter(PenaltyCalculation.billing_cycle_id == billing_cycle_id)
        contract_score_query = contract_score_query.filter(MonthlyContractScore.billing_cycle_id == billing_cycle_id)
    if contract_id:
        inspection_query = inspection_query.filter(Inspection.contract_id == contract_id)
        penalty_query = penalty_query.filter(PenaltyCalculation.contract_id == contract_id)
        contract_score_query = contract_score_query.filter(MonthlyContractScore.contract_id == contract_id)

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
    billing_cycle_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    station_id: int | None = None,
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from_date, to_date, _cycle = _apply_cycle_dates(db, billing_cycle_id, from_date, to_date)

    inspections = _filtered_inspections(db, user, from_date, to_date, station_id, contract_id).order_by(Inspection.inspection_date).all()

    penalty_query = db.query(PenaltyCalculation)
    contract_score_query = db.query(MonthlyContractScore)
    if not is_admin_scope(user):
        penalty_query = apply_contract_scope(penalty_query, PenaltyCalculation.contract_id, db, user)
        contract_score_query = apply_contract_scope(contract_score_query, MonthlyContractScore.contract_id, db, user)

    if billing_cycle_id:
        penalty_query = penalty_query.filter(PenaltyCalculation.billing_cycle_id == billing_cycle_id)
        contract_score_query = contract_score_query.filter(MonthlyContractScore.billing_cycle_id == billing_cycle_id)
    if contract_id:
        penalty_query = penalty_query.filter(PenaltyCalculation.contract_id == contract_id)
        contract_score_query = contract_score_query.filter(MonthlyContractScore.contract_id == contract_id)

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

        active_entries = [e for e in getattr(ins, "entries", []) if not getattr(e, "is_deleted", False)]
        if active_entries:
            for entry in active_entries:
                grade_dist[entry.grade_code] += 1
        else:
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
    latest_contract_score = contract_score_query.order_by(MonthlyContractScore.calculated_at.desc()).first()
    latest_score = float(latest_contract_score.average_score) if latest_contract_score else (score_trend[-1]["value"] if score_trend else 0)

    scoped_contract_query = apply_contract_scope(db.query(Contract), Contract.id, db, user) if not is_admin_scope(user) else db.query(Contract)
    scoped_station_query = apply_station_scope(db.query(Station), Station.id, db, user) if not is_admin_scope(user) else db.query(Station)

    contract_score_rows = [
        {
            "label": f"Contract {s.contract_id}/Cycle {s.billing_cycle_id}",
            "value": s.average_score,
            "penalty": s.is_penalty_applicable,
            "contract_id": s.contract_id,
            "billing_cycle_id": s.billing_cycle_id,
        }
        for s in contract_score_query.order_by(MonthlyContractScore.calculated_at.desc()).limit(12).all()
    ]

    return {
        "summary": {
            "contracts": scoped_contract_query.with_entities(func.count(Contract.id)).scalar() or 0,
            "stations": scoped_station_query.with_entities(func.count(Station.id)).scalar() or 0,
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
        "contract_scores": contract_score_rows,
        "role_view": user.role.code.value,
    }


@router.get("/contract-wise-score")
def contract_wise_score(
    billing_cycle_id: int | None = None,
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(MonthlyContractScore)
    if not is_admin_scope(user):
        query = apply_contract_scope(query, MonthlyContractScore.contract_id, db, user)
    if billing_cycle_id:
        query = query.filter(MonthlyContractScore.billing_cycle_id == billing_cycle_id)
    if contract_id:
        query = query.filter(MonthlyContractScore.contract_id == contract_id)
    return query.order_by(MonthlyContractScore.calculated_at.desc()).limit(50).all()


@router.get("/pending-reviews")
def pending_reviews(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return apply_review_scope(db.query(Inspection), db, user).limit(50).all()
'''

DASHBOARD_VIEW = r'''
<template>
  <AppLayout>
    <section class="card hero-panel">
      <div class="toolbar">
        <div>
          <h1>Operations Cleanliness Command Dashboard</h1>
          <p class="hero-subtitle">Monitor KPI-6 inspections, station cleanliness trend, review backlog, contractor performance and GM/Ops-approved monthly penalties.</p>
        </div>
        <div class="role-pill">{{ auth.user?.role }} view</div>
      </div>
      <div class="filter-grid section-gap dashboard-filter-grid">
        <label>
          <span class="label">Billing month</span>
          <select class="input" v-model="filters.billing_cycle_id">
            <option value="">All months</option>
            <option v-for="cycle in billingCycles" :key="cycle.id" :value="cycle.id">{{ cycleLabel(cycle) }}</option>
          </select>
        </label>
        <label><span class="label">Period</span><select class="input" v-model="filters.period"><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="yearly">Yearly</option></select></label>
        <label><span class="label">From</span><input class="input" type="date" v-model="filters.from_date" :max="today"/></label>
        <label><span class="label">To</span><input class="input" type="date" v-model="filters.to_date" :max="today"/></label>
        <label><span class="label">Contract</span><select class="input" v-model="filters.contract_id"><option value="">All contracts</option><option v-for="c in master.contracts" :key="c.id" :value="c.id">{{ c.contract_code }}</option></select></label>
        <label><span class="label">Station</span><select class="input" v-model="filters.station_id"><option value="">All stations</option><option v-for="s in master.stations" :key="s.id" :value="s.id">{{ s.station_name }}</option></select></label>
        <button class="btn btn-primary" @click="load">Apply Filters</button>
      </div>
    </section>

    <div class="stat-grid section-gap">
      <StatCard label="Contracts" :value="analytics.summary?.contracts ?? 0" foot="Active contracts" />
      <StatCard label="Stations" :value="analytics.summary?.stations ?? 0" foot="Mapped stations" />
      <StatCard label="Inspections" :value="analytics.summary?.inspections ?? 0" foot="In selected period/month" />
      <StatCard label="Pending Reviews" :value="analytics.summary?.pending_reviews ?? 0" foot="Action required" />
      <StatCard label="Penalty Amount" :value="currency(analytics.summary?.penalty_amount || 0)" foot="GM-approved monthly penalties" />
    </div>

    <div class="grid grid-3 section-gap dashboard-grid">
      <div class="card span-2">
        <div class="card-title"><h2>KPI-6 Score Trend</h2><span class="badge blue">{{ filters.period }}</span></div>
        <SimpleLineChart :items="analytics.score_trend || []" />
      </div>
      <div class="card">
        <div class="card-title"><h2>Latest Contract Score</h2><span class="badge" :class="scoreClass(latestScore)">{{ latestScore }}%</span></div>
        <DonutChart :value="latestScore" label="KPI-6">
          <p class="muted">Penalty threshold is 90%. Monthly penalty rows are generated only after GM/Ops final approval.</p>
          <RouterLink class="btn btn-secondary" to="/kpi">Open KPI module</RouterLink>
        </DonutChart>
      </div>
    </div>

    <div class="grid grid-2 section-gap">
      <div class="card">
        <div class="card-title"><h2>Station-wise Score</h2><span class="badge">Score %</span></div>
        <SimpleBarChart :items="analytics.station_scores || []" suffix="%" />
      </div>
      <div class="card">
        <div class="card-title"><h2>Inspection Volume</h2><span class="badge">Count</span></div>
        <SimpleBarChart :items="analytics.inspection_volume || []" />
      </div>
    </div>

    <div class="grid grid-2 section-gap">
      <div class="card">
        <div class="card-title"><h2>Grade Distribution</h2><span class="badge blue">A to F</span></div>
        <SimpleBarChart :items="analytics.grade_distribution || []" />
      </div>
      <div class="card">
        <div class="card-title"><h2>Report Downloads</h2><span class="badge green">PDF</span></div>
        <p class="muted">Download the inspection register for the selected billing month, contract, station and date range.</p>
        <div class="toolbar report-actions">
          <button class="btn btn-primary" @click="downloadRangePdf">Download Filtered PDF</button>
          <RouterLink class="btn btn-outline" to="/reports">Advanced Reports</RouterLink>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import StatCard from '../components/StatCard.vue'
import SimpleBarChart from '../components/SimpleBarChart.vue'
import SimpleLineChart from '../components/SimpleLineChart.vue'
import DonutChart from '../components/DonutChart.vue'
import { api, downloadBlob } from '../services/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const analytics = ref({ summary: {} })
const master = ref({ contracts: [], stations: [], billing_cycles: [] })
const filters = reactive({
  period: 'monthly',
  billing_cycle_id: '',
  from_date: '2026-01-01',
  to_date: new Date().toISOString().split('T')[0],
  contract_id: '',
  station_id: ''
})
const latestScore = computed(() => Number(analytics.value.summary?.latest_score || analytics.value.score_trend?.at(-1)?.value || 0))
const today = new Date().toISOString().split('T')[0]

const billingCycles = computed(() => [...(master.value.billing_cycles || [])].sort((a, b) => String(b.start_date || '').localeCompare(String(a.start_date || ''))))
const selectedCycle = computed(() => billingCycles.value.find((cycle) => Number(cycle.id) === Number(filters.billing_cycle_id)) || null)

function scoreClass(v){ return v >= 90 ? 'green' : v >= 80 ? 'amber' : 'red' }
function currency(v){ return new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', maximumFractionDigits:0 }).format(v || 0) }
function cycleLabel(cycle){ return cycle ? `${cycle.name || cycle.code || `Cycle ${cycle.id}`} · ${formatDate(cycle.start_date)} to ${formatDate(cycle.end_date)}` : '-' }
function formatDate(value){ if(!value) return '-'; return new Date(value).toLocaleDateString('en-IN') }

function syncCycleDates() {
  if (!selectedCycle.value) return
  filters.from_date = selectedCycle.value.start_date || filters.from_date
  filters.to_date = selectedCycle.value.end_date || filters.to_date
}

function params(){
  syncCycleDates()
  return Object.fromEntries(Object.entries(filters).filter(([_,v]) => v !== '' && v !== null))
}

function reportParams(){
  syncCycleDates()
  const out = { ...filters }
  delete out.period
  delete out.billing_cycle_id
  return Object.fromEntries(Object.entries(out).filter(([_,v]) => v !== '' && v !== null))
}

async function load(){ analytics.value = (await api.get('/dashboard/analytics', { params: params() })).data }

async function loadMaster(){
  master.value = (await api.get('/master/bootstrap')).data
  if (!filters.billing_cycle_id && billingCycles.value.length) {
    filters.billing_cycle_id = String(billingCycles.value[0].id)
    syncCycleDates()
  }
}

async function downloadRangePdf(){ await downloadBlob('/reports/inspections/pdf', reportParams(), 'inspection-register.pdf') }
onMounted(async()=>{ await loadMaster(); await load() })
</script>

<style scoped>
.dashboard-grid { align-items: stretch; }
.report-actions { justify-content: flex-start; }
.dashboard-filter-grid { grid-template-columns: 1.4fr 1fr 1fr 1fr 1.2fr 1.2fr auto; }
@media (max-width: 1180px) {
  .dashboard-filter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 720px) {
  .dashboard-filter-grid { grid-template-columns: 1fr; }
}
</style>
'''


def patch_kpi_dashboard_view(path):
    content = path.read_text(encoding="utf-8")
    original = content

    content = content.replace(
        "Select the billing month and contract name, calculate KPI-6, then check the station drill-down.\n        Stations with no SM/EIT inspection or low score explain why a penalty was generated.",
        "Select the billing month and contract name, calculate KPI-6 after GM/Ops final approval, then check the station drill-down.\n        Only GM/Ops-approved inspections contribute to monthly KPI score and penalty; pending inspections block calculation."
    )

    content = content.replace(
        "KPI-6 compares the contract average against the configured contract threshold.\n          Penalty amount is calculated from monthly bill value and contract penalty percentage.",
        "KPI-6 compares the contract average against the configured contract threshold after GM/Ops final approval.\n          Penalty amount is calculated from monthly bill value and contract penalty percentage only for approved monthly inspection data."
    )

    content = content.replace(
        "{{ calculating ? 'Calculating...' : 'Calculate selected contract' }}",
        "{{ calculating ? 'Checking GM approvals...' : 'Calculate after GM approval' }}"
    )

    if content == original:
        print("KpiDashboardView.vue text already patched or expected labels not found; no change made")
        return
    path.write_text(content, encoding="utf-8")


def main():
    root = find_project_root()
    print("Project root:", root)

    write(root / "backend" / "app" / "services" / "kpi_calculation_service.py", KPI_SERVICE)
    print("Updated backend/app/services/kpi_calculation_service.py")

    write(root / "backend" / "app" / "api" / "v1" / "endpoints" / "kpi.py", KPI_ENDPOINT)
    print("Updated backend/app/api/v1/endpoints/kpi.py")

    write(root / "backend" / "app" / "schemas" / "kpi.py", KPI_SCHEMA)
    print("Updated backend/app/schemas/kpi.py")

    write(root / "backend" / "app" / "api" / "v1" / "endpoints" / "dashboard.py", DASHBOARD_ENDPOINT)
    print("Updated backend/app/api/v1/endpoints/dashboard.py")

    write(root / "frontend" / "src" / "views" / "DashboardView.vue", DASHBOARD_VIEW)
    print("Updated frontend/src/views/DashboardView.vue")

    kpi_dashboard = root / "frontend" / "src" / "views" / "KpiDashboardView.vue"
    if kpi_dashboard.exists():
        patch_kpi_dashboard_view(kpi_dashboard)
        print("Patched frontend/src/views/KpiDashboardView.vue guidance labels")
    else:
        print("Skipped KpiDashboardView.vue; file not found")

    print("")
    print("KPI GM approval/month-contract patch applied successfully.")
    print("Now rebuild: docker compose up -d --build api frontend")
    print("No DB migration required.")


if __name__ == "__main__":
    main()
