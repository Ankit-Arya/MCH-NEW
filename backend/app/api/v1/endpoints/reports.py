
from datetime import date
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_station_access
from app.models.all_models import Inspection, InspectionStatus, InspectionType, User

router = APIRouter()


def _inspection_score(inspection: Inspection) -> float:
    if not inspection.attribute_scores:
        return 0.0
    return round(sum(s.grade_percentage for s in inspection.attribute_scores) / len(inspection.attribute_scores), 2)


def _query_inspections(db: Session, from_date=None, to_date=None, station_id=None, contract_id=None, submitted_by=None, inspection_type=None, status=None):
    q = db.query(Inspection).order_by(Inspection.inspection_date.desc(), Inspection.id.desc())
    if from_date:
        q = q.filter(Inspection.inspection_date >= from_date)
    if to_date:
        q = q.filter(Inspection.inspection_date <= to_date)
    if station_id:
        q = q.filter(Inspection.station_id == station_id)
    if contract_id:
        q = q.filter(Inspection.contract_id == contract_id)
    if submitted_by:
        q = q.filter(Inspection.submitted_by == submitted_by)
    if inspection_type:
        q = q.filter(Inspection.inspection_type == inspection_type)
    if status:
        q = q.filter(Inspection.status == status)
    return q


def _row(i: Inspection) -> dict:
    return {
        "id": i.id,
        "inspection_no": i.inspection_no,
        "inspection_date": i.inspection_date.isoformat(),
        "inspection_type": i.inspection_type.value,
        "status": i.status.value,
        "station_id": i.station_id,
        "station_name": i.station.station_name if i.station else None,
        "contract_id": i.contract_id,
        "contract_code": i.contract.contract_code if i.contract else None,
        "submitted_by": i.submitted_by,
        "submitted_by_name": i.submitter.name if i.submitter else None,
        "score": _inspection_score(i),
        "media_count": len(i.media or []),
    }


@router.get("/inspections/search")
def search_inspection_reports(
    from_date: date | None = None,
    to_date: date | None = None,
    station_id: int | None = None,
    contract_id: int | None = None,
    submitted_by: int | None = None,
    inspection_type: InspectionType | None = None,
    status: InspectionStatus | None = None,
    limit: int = Query(500, le=2000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return [_row(i) for i in _query_inspections(db, from_date, to_date, station_id, contract_id, submitted_by, inspection_type, status).limit(limit).all()]


@router.get("/inspection/{inspection_id}/pdf")
def inspection_pdf(inspection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    require_station_access(db, user, inspection.station_id)
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=24)
    story = []
    story.append(Paragraph("DMRC MCH KPI-6 Inspection Report", styles["Title"]))
    story.append(Paragraph(f"Inspection No: <b>{inspection.inspection_no}</b>", styles["Normal"]))
    story.append(Paragraph(f"Station: <b>{inspection.station.station_name if inspection.station else inspection.station_id}</b> | Contract: <b>{inspection.contract.contract_code if inspection.contract else inspection.contract_id}</b>", styles["Normal"]))
    story.append(Paragraph(f"Inspector: <b>{inspection.submitter.name if inspection.submitter else inspection.submitted_by}</b> | Type: <b>{inspection.inspection_type.value}</b> | Status: <b>{inspection.status.value}</b>", styles["Normal"]))
    story.append(Paragraph(f"Date: <b>{inspection.inspection_date}</b> | GPS: {inspection.latitude}, {inspection.longitude} | Score: <b>{_inspection_score(inspection)}%</b>", styles["Normal"]))
    story.append(Spacer(1, 12))
    data = [["Attribute", "Grade", "Score", "Remarks"]]
    for s in inspection.attribute_scores:
        data.append([s.attribute.name if s.attribute else s.attribute_id, s.grade_code, f"{s.grade_percentage}%", s.remarks or ""])
    if len(data) == 1:
        data.append(["No scores", "", "", ""])
    table = Table(data, repeatRows=1, colWidths=[230, 60, 70, 150])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#092b6f")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#dbe3f0")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7faff")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph(f"Evidence files attached/uploaded: <b>{len(inspection.media or [])}</b>", styles["Normal"]))
    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={inspection.inspection_no}.pdf"})


@router.get("/inspections/pdf")
def inspections_pdf(
    from_date: date | None = None,
    to_date: date | None = None,
    station_id: int | None = None,
    contract_id: int | None = None,
    submitted_by: int | None = None,
    inspection_type: InspectionType | None = None,
    status: InspectionStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inspections = _query_inspections(db, from_date, to_date, station_id, contract_id, submitted_by, inspection_type, status).limit(2000).all()
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=22, leftMargin=22, topMargin=24, bottomMargin=20)
    story = [Paragraph("DMRC MCH KPI-6 Inspection Register", styles["Title"])]
    story.append(Paragraph(f"Filters: From {from_date or '-'} To {to_date or '-'} | Station {station_id or 'All'} | Contract {contract_id or 'All'} | Inspector {submitted_by or 'All'}", styles["Normal"]))
    story.append(Spacer(1, 10))
    data = [["Inspection No", "Date", "Station", "Contract", "Inspector", "Type", "Status", "Score", "Media"]]
    for i in inspections:
        data.append([
            i.inspection_no,
            str(i.inspection_date),
            i.station.station_name if i.station else str(i.station_id),
            i.contract.contract_code if i.contract else str(i.contract_id),
            i.submitter.name if i.submitter else str(i.submitted_by),
            i.inspection_type.value.replace("_INSPECTION", ""),
            i.status.value,
            f"{_inspection_score(i)}%",
            str(len(i.media or [])),
        ])
    if len(data) == 1:
        data.append(["No records", "", "", "", "", "", "", "", ""])
    table = Table(data, repeatRows=1, colWidths=[125, 65, 100, 100, 105, 65, 120, 45, 40])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#092b6f")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#dbe3f0")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7faff")]),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=inspection-register.pdf"})
