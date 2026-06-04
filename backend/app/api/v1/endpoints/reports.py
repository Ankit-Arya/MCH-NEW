from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape
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
from app.models.all_models import Inspection, InspectionEntry, InspectionMedia, InspectionStatus, InspectionType, MediaType, User

router = APIRouter()


def _inspection_score(inspection: Inspection) -> float:
    entries = [e for e in getattr(inspection, "entries", []) if not e.is_deleted]
    if entries:
        return round(sum(e.grade_percentage for e in entries) / len(entries), 2)
    if inspection.attribute_scores:
        return round(sum(s.grade_percentage for s in inspection.attribute_scores) / len(inspection.attribute_scores), 2)
    return 0.0


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


def _media_counts(db: Session, entry_id: int) -> tuple[int, int]:
    photos = db.query(InspectionMedia).filter_by(inspection_entry_id=entry_id, media_type=MediaType.PHOTO, is_deleted=False).count()
    videos = db.query(InspectionMedia).filter_by(inspection_entry_id=entry_id, media_type=MediaType.VIDEO, is_deleted=False).count()
    return photos, videos


def _row(i: Inspection) -> dict:
    entries = [e for e in getattr(i, "entries", []) if not e.is_deleted]
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
        "entry_count": len(entries),
        "media_count": len([m for m in (i.media or []) if not m.is_deleted]),
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
    story.append(Paragraph("DMRC MCH KPI-6 Entry-wise Inspection Report", styles["Title"]))
    story.append(Paragraph(f"Inspection No: <b>{escape(inspection.inspection_no)}</b>", styles["Normal"]))
    story.append(Paragraph(f"Station: <b>{escape(inspection.station.station_name if inspection.station else str(inspection.station_id))}</b> | Contract: <b>{escape(inspection.contract.contract_code if inspection.contract else str(inspection.contract_id))}</b>", styles["Normal"]))
    story.append(Paragraph(f"Inspector: <b>{escape(inspection.submitter.name if inspection.submitter else str(inspection.submitted_by))}</b> | Type: <b>{inspection.inspection_type.value}</b> | Status: <b>{inspection.status.value}</b>", styles["Normal"]))
    story.append(Paragraph(f"Date: <b>{inspection.inspection_date}</b> | Header GPS: {inspection.latitude}, {inspection.longitude} | Score: <b>{_inspection_score(inspection)}%</b>", styles["Normal"]))
    story.append(Spacer(1, 12))

    entries = db.query(InspectionEntry).filter_by(inspection_id=inspection.id, is_deleted=False).order_by(InspectionEntry.id).all()
    if entries:
        data = [["Entry", "Attribute", "Sub-area", "Grade", "Score", "Photo/Video", "Captured", "Remarks"]]
        for e in entries:
            photos, videos = _media_counts(db, e.id)
            captured = e.captured_at.strftime("%d-%m-%Y %H:%M") if e.captured_at else "-"
            gps = f"GPS {e.captured_latitude or '-'}, {e.captured_longitude or '-'} acc {e.gps_accuracy or '-'}m"
            data.append([
                e.entry_no,
                escape(e.attribute.name if e.attribute else str(e.attribute_id)),
                escape(e.sub_area.name if e.sub_area else str(e.sub_area_id)),
                e.grade_code,
                f"{e.grade_percentage}%",
                f"P:{photos} V:{videos}",
                f"{captured} | {gps}",
                escape(e.remarks or ""),
            ])
        table = Table(data, repeatRows=1, colWidths=[55, 105, 95, 42, 42, 58, 105, 95])
    else:
        data = [["Attribute", "Grade", "Score", "Remarks"]]
        for s in inspection.attribute_scores:
            data.append([s.attribute.name if s.attribute else s.attribute_id, s.grade_code, f"{s.grade_percentage}%", s.remarks or ""])
        if len(data) == 1:
            data.append(["No entry records", "", "", ""])
        table = Table(data, repeatRows=1, colWidths=[230, 60, 70, 150])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#092b6f")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#dbe3f0")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7.5),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7faff")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph(f"Evidence files uploaded: <b>{len([m for m in (inspection.media or []) if not m.is_deleted])}</b>", styles["Normal"]))
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
    story = [Paragraph("DMRC MCH KPI-6 Entry-wise Inspection Register", styles["Title"])]
    story.append(Paragraph(f"Filters: From {from_date or '-'} To {to_date or '-'} | Station {station_id or 'All'} | Contract {contract_id or 'All'} | Inspector {submitted_by or 'All'}", styles["Normal"]))
    story.append(Spacer(1, 10))
    data = [["Inspection No", "Date", "Station", "Inspector", "Status", "Entry", "Attribute", "Sub-area", "Grade", "P/V"]]
    for i in inspections:
        entries = db.query(InspectionEntry).filter_by(inspection_id=i.id, is_deleted=False).order_by(InspectionEntry.id).all()
        if entries:
            for e in entries:
                photos, videos = _media_counts(db, e.id)
                data.append([
                    i.inspection_no,
                    str(i.inspection_date),
                    i.station.station_name if i.station else str(i.station_id),
                    i.submitter.name if i.submitter else str(i.submitted_by),
                    i.status.value,
                    e.entry_no,
                    e.attribute.name if e.attribute else str(e.attribute_id),
                    e.sub_area.name if e.sub_area else str(e.sub_area_id),
                    f"{e.grade_code} ({e.grade_percentage}%)",
                    f"{photos}/{videos}",
                ])
        else:
            data.append([i.inspection_no, str(i.inspection_date), i.station.station_name if i.station else str(i.station_id), i.submitter.name if i.submitter else str(i.submitted_by), i.status.value, "-", "No entry records", "", f"{_inspection_score(i)}%", str(len(i.media or []))])
    if len(data) == 1:
        data.append(["No records", "", "", "", "", "", "", "", "", ""])
    table = Table(data, repeatRows=1, colWidths=[115, 58, 95, 95, 105, 48, 110, 105, 62, 35])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#092b6f")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#dbe3f0")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7faff")]),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=inspection-register-entry-wise.pdf"})
