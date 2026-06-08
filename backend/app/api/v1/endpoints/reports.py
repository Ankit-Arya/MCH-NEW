from datetime import date
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.graphics import renderPDF
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as PlatypusImage
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_station_access
from app.models.all_models import Inspection, InspectionEntry, InspectionMedia, InspectionStatus, InspectionType, MediaType, User
from app.services.media_service import download_bytes, get_external_object_url
router = APIRouter()

REPORT_PRIMARY = colors.white
REPORT_PRIMARY_DARK = colors.black
REPORT_BORDER = colors.HexColor("#8a8a8a")
REPORT_MUTED = colors.HexColor("#555555")
REPORT_SURFACE = colors.white
REPORT_ROW_ALT = colors.HexColor("#f2f2f2")
REPORT_TEXT = colors.black


def _inspection_score(inspection: Inspection) -> float:
    entries = [e for e in getattr(inspection, "entries", []) if not e.is_deleted]
    if entries:
        return round(sum(e.grade_percentage for e in entries) / len(entries), 2)
    if inspection.attribute_scores:
        return round(sum(s.grade_percentage for s in inspection.attribute_scores) / len(inspection.attribute_scores), 2)
    return 0.0


def _configure_pdf_styles():
    styles = getSampleStyleSheet()

    styles["Title"].fontName = "Helvetica-Bold"
    styles["Title"].fontSize = 22
    styles["Title"].leading = 26
    styles["Title"].alignment = TA_CENTER
    styles["Title"].textColor = REPORT_TEXT

    styles["Normal"].fontName = "Helvetica"
    styles["Normal"].fontSize = 9
    styles["Normal"].leading = 12
    styles["Normal"].textColor = REPORT_TEXT

    styles["BodyText"].fontName = "Helvetica"
    styles["BodyText"].fontSize = 8.5
    styles["BodyText"].leading = 11
    styles["BodyText"].textColor = REPORT_TEXT

    styles["Heading3"].fontName = "Helvetica-Bold"
    styles["Heading3"].fontSize = 12
    styles["Heading3"].leading = 14
    styles["Heading3"].textColor = REPORT_PRIMARY_DARK
    styles["Heading3"].spaceAfter = 4

    styles["Italic"].fontName = "Helvetica-Oblique"
    styles["Italic"].fontSize = 8.5
    styles["Italic"].leading = 11
    styles["Italic"].textColor = REPORT_MUTED

    styles.add(ParagraphStyle(
        name="SectionTitle",
        parent=styles["Heading3"],
        fontSize=11,
        leading=13,
        textColor=REPORT_PRIMARY_DARK,
        spaceBefore=2,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="HeaderBadge",
        parent=styles["BodyText"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        textColor=REPORT_TEXT,
    ))
    styles.add(ParagraphStyle(
        name="HeaderBadgeSub",
        parent=styles["BodyText"],
        alignment=TA_CENTER,
        fontSize=7,
        leading=8,
        textColor=REPORT_MUTED,
    ))
    styles.add(ParagraphStyle(
        name="HeaderTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=23,
        alignment=TA_CENTER,
        textColor=REPORT_TEXT,
    ))
    styles.add(ParagraphStyle(
        name="HeaderSubtitle",
        parent=styles["BodyText"],
        alignment=TA_CENTER,
        fontSize=8,
        leading=10,
        textColor=REPORT_MUTED,
    ))
    styles.add(ParagraphStyle(
        name="MetaLabel",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=REPORT_PRIMARY_DARK,
    ))
    styles.add(ParagraphStyle(
        name="MetaValue",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11,
        textColor=REPORT_TEXT,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.6,
        leading=9,
        textColor=REPORT_TEXT,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        parent=styles["BodyText"],
        fontSize=7.4,
        leading=9,
        textColor=REPORT_TEXT,
        splitLongWords=True,
    ))
    styles.add(ParagraphStyle(
        name="TableCellCenter",
        parent=styles["TableCell"],
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="StatLabel",
        parent=styles["BodyText"],
        fontSize=7.8,
        leading=9,
        alignment=TA_CENTER,
        textColor=REPORT_MUTED,
    ))
    styles.add(ParagraphStyle(
        name="StatValue",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=17,
        alignment=TA_CENTER,
        textColor=REPORT_PRIMARY_DARK,
    ))
    return styles


def _safe_text(value, fallback: str = "-") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return escape(text) if text else fallback


def _p(value, style) -> Paragraph:
    lines = str(value).splitlines() if value is not None else []
    if not lines:
        return Paragraph("-", style)
    return Paragraph("<br/>".join(_safe_text(line) for line in lines), style)


def _brand_badge(primary_text: str, secondary_text: str, styles) -> Table:
    badge = Table(
        [[Paragraph(primary_text, styles["HeaderBadge"])], [Paragraph(secondary_text, styles["HeaderBadgeSub"])]],
        colWidths=[84],
    )
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, REPORT_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return badge


def _build_dmrc_logo(styles, max_width: int = 112, max_height: int = 68):
    candidate_paths = [
        Path("/app/frontend_assets/dmrc-logo.svg"),
        Path(__file__).resolve().parents[5] / "frontend" / "src" / "assets" / "dmrc-logo.svg",
    ]
    try:
        from svglib.svglib import svg2rlg

        logo_path = next((path for path in candidate_paths if path.exists()), None)
        if not logo_path:
            raise FileNotFoundError("DMRC logo SVG not found in expected paths")

        drawing = svg2rlg(str(logo_path))
        if drawing is None or not getattr(drawing, "width", None) or not getattr(drawing, "height", None):
            raise ValueError("Unable to parse DMRC logo SVG")

        scale = min(max_width / drawing.width, max_height / drawing.height)
        drawing.scale(scale, scale)
        drawing.width *= scale
        drawing.height *= scale
        return renderPDF.GraphicsFlowable(drawing)
    except Exception:
        return _brand_badge("DMRC", "Delhi Metro Rail Corporation", styles)


def _build_report_header(styles, title: str, subtitle: str | None = None) -> Table:
    title_markup = escape(title).replace("\n", "<br/>")
    header = Table(
        [[
            _build_dmrc_logo(styles),
            [
                Paragraph(title_markup, styles["HeaderTitle"])
            ],
        ]],
        colWidths=[120, 415],
        hAlign="CENTER",
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 10),
        ("TOPPADDING", (0, 0), (0, 0), 0),
        ("BOTTOMPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (1, 0), (1, 0), 0),
        ("BOTTOMPADDING", (1, 0), (1, 0), 8),
    ]))
    return header


def _build_metadata_table(inspection: Inspection, styles) -> Table:
    metadata = [
        [
            Paragraph("Inspection No", styles["MetaLabel"]),
            Paragraph(f"<b>{_safe_text(inspection.inspection_no)}</b>", styles["MetaValue"]),
            Paragraph("Inspection Date", styles["MetaLabel"]),
            Paragraph(
                f"<b>{_safe_text(inspection.inspection_date.strftime('%d-%m-%Y') if inspection.inspection_date else '-')}</b>",
                styles["MetaValue"],
            ),
        ],
        [
            Paragraph("Station", styles["MetaLabel"]),
            Paragraph(_safe_text(inspection.station.station_name if inspection.station else inspection.station_id), styles["MetaValue"]),
            Paragraph("Contract", styles["MetaLabel"]),
            Paragraph(_safe_text(inspection.contract.contract_code if inspection.contract else inspection.contract_id), styles["MetaValue"]),
        ],
        [
            Paragraph("Inspector", styles["MetaLabel"]),
            Paragraph(_safe_text(inspection.submitter.name if inspection.submitter else inspection.submitted_by), styles["MetaValue"]),
            Paragraph("Inspection Type", styles["MetaLabel"]),
            Paragraph(_safe_text(inspection.inspection_type.value), styles["MetaValue"]),
        ],
        [
            Paragraph("Status", styles["MetaLabel"]),
            Paragraph(_safe_text(inspection.status.value), styles["MetaValue"]),
            Paragraph("Inspection Score", styles["MetaLabel"]),
            Paragraph(f"<b>{_inspection_score(inspection)}%</b>", styles["MetaValue"]),
        ],
        # [
        #     Paragraph("Header GPS", styles["MetaLabel"]),
        #     Paragraph(
        #         _safe_text(f"{inspection.latitude or '-'}, {inspection.longitude or '-'}"),
        #         styles["MetaValue"],
        #     ),
        #     Paragraph("", styles["MetaLabel"]),
        #     Paragraph("", styles["MetaValue"]),
        # ],
    ]
    table = Table(metadata, colWidths=[78, 190, 78, 189])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), REPORT_SURFACE),
        ("BACKGROUND", (2, 0), (2, -1), REPORT_SURFACE),
        ("SPAN", (1, 4), (3, 4)),
        ("BOX", (0, 0), (-1, -1), 0.8, REPORT_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, REPORT_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _build_summary_table(total_media: int, total_photos: int, total_videos: int, styles) -> Table:
    data = [[
        [Paragraph("Evidence Files", styles["StatLabel"]), Paragraph(str(total_media), styles["StatValue"])],
        [Paragraph("Photo Previews", styles["StatLabel"]), Paragraph(str(total_photos), styles["StatValue"])],
        [Paragraph("Video Links", styles["StatLabel"]), Paragraph(str(total_videos), styles["StatValue"])],
    ]]
    table = Table(data, colWidths=[176, 176, 183])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, REPORT_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, REPORT_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def _draw_pdf_footer(canvas, doc):
    canvas.saveState()
    page_width = doc.pagesize[0]
    footer_y = doc.bottomMargin - 6
    canvas.setStrokeColor(REPORT_BORDER)
    canvas.line(doc.leftMargin, footer_y + 10, page_width - doc.rightMargin, footer_y + 10)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(REPORT_MUTED)
    canvas.drawString(doc.leftMargin, footer_y, "MCH KPI-6 Inspection Platform")
    canvas.drawRightString(page_width - doc.rightMargin, footer_y, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


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

# This is a helper function which returns a Platypus Image object scaled to fit the bounding box   
# 
# Args:
#         image_bytes: Raw image data in bytes.
#         max_width: Maximum allowed width in points.
#         max_height: Maximum allowed height in points.


def _build_thumbnail_flowable(image_bytes: bytes, max_width: int = 150, max_height: int = 110) -> PlatypusImage:
    image_buffer = BytesIO(image_bytes)
    width, height = ImageReader(image_buffer).getSize()
    scale = min(max_width / width, max_height / height)
    thumb_width = max(1, width * scale)
    thumb_height = max(1, height * scale)
    image_buffer.seek(0)
    thumbnail = PlatypusImage(image_buffer, width=thumb_width, height=thumb_height)
    thumbnail.hAlign = "CENTER"
    return thumbnail
 

# def _build_photo_preview_table(inspection: Inspection, styles):
#     photo_media = [
#         media for media in (inspection.media or [])
#         if not media.is_deleted
#         and media.media_type == MediaType.PHOTO
#         and (not media.mime_type or media.mime_type.startswith("image/"))
#     ]
#     if not photo_media:
#         return []

#     story = [Paragraph("Photo Evidence Preview", styles["Heading3"]), Spacer(1, 6)]
#     cells = []
#     unavailable_count = 0
#     for media in photo_media:
#         try:
#             thumbnail = _build_thumbnail_flowable(download_bytes(media.object_path))
#             label = media.sub_area.name if media.sub_area else media.original_file_name
#             cells.append([thumbnail, Spacer(1, 4), Paragraph(label, styles["BodyText"])])
#         except Exception:
#             unavailable_count += 1

#     if not cells:
#         return [Paragraph("Photo previews are unavailable for this inspection.", styles["Normal"])]

#     columns = 2
#     rows = [cells[index:index + columns] for index in range(0, len(cells), columns)]
#     if rows and len(rows[-1]) < columns:
#         rows[-1].extend([""] * (columns - len(rows[-1])))

#     preview_table = Table(rows, colWidths=[250, 250], hAlign="LEFT")
#     preview_table.setStyle(TableStyle([
#         ("VALIGN", (0, 0), (-1, -1), "TOP"),
#         ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe3f0")),
#         ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe3f0")),
#         ("LEFTPADDING", (0, 0), (-1, -1), 8),
#         ("RIGHTPADDING", (0, 0), (-1, -1), 8),
#         ("TOPPADDING", (0, 0), (-1, -1), 8),
#         ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
#     ]))
#     story.append(preview_table)
#     if unavailable_count:
#         story.extend([
#             Spacer(1, 6),
#             Paragraph(f"{unavailable_count} photo preview(s) could not be loaded.", styles["Italic"]),
#         ])
#     return story
def _build_photo_preview_table(inspection: Inspection, styles):
    photo_media = [
        media for media in (inspection.media or [])
        if not media.is_deleted
        and media.media_type == MediaType.PHOTO
        and (not media.mime_type or media.mime_type.startswith("image/"))
    ]
    if not photo_media:
        return []

    story = [Paragraph("Photo Evidence Preview", styles["Heading3"]), Spacer(1, 6)]
    cells = []
    unavailable_count = 0

    for media in photo_media:
        try:
            thumbnail = _build_thumbnail_flowable(download_bytes(media.object_path))
            label = media.sub_area.name if media.sub_area else media.original_file_name
            safe_label = escape(label or "Photo")

            cells.append([
                thumbnail,
                Spacer(1, 4),
                Paragraph(safe_label, styles["BodyText"]),
            ])
        except Exception:
            unavailable_count += 1

    if not cells:
        return [Paragraph("Photo previews are unavailable for this inspection.", styles["Normal"])]

    columns = 2
    rows = [cells[index:index + columns] for index in range(0, len(cells), columns)]
    if rows and len(rows[-1]) < columns:
        rows[-1].extend([""] * (columns - len(rows[-1])))

    preview_table = Table(rows, colWidths=[250, 250], hAlign="LEFT")
    preview_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe3f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dbe3f0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(preview_table)

    if unavailable_count:
        story.extend([
            Spacer(1, 6),
            Paragraph(f"{unavailable_count} photo preview(s) could not be loaded.", styles["Italic"]),
        ])

    return story

# Provide evidence video URL from minio in the downloaded PDF
# def _build_video_link_section(inspection: Inspection, styles):
#     video_media = [
#         media for media in (inspection.media or [])
#         if not media.is_deleted and media.media_type == MediaType.VIDEO
#     ]
#     if not video_media:
#         return []

#     story = [Paragraph("Video Evidence Links", styles["Heading3"]), Spacer(1, 6)]
#     unavailable_count = 0
#     for index, media in enumerate(video_media, start=1):
#         try:
#             video_url = get_external_object_url(media.object_path)
#             label = media.sub_area.name if media.sub_area else media.original_file_name
#             safe_label = escape(label or f"Video {index}")
#             safe_href = escape(video_url, {'"': "&quot;"})
#             safe_link_text = escape(video_url)
#             story.append(
#                 Paragraph(
#                     f'{index}. <b>{safe_label}</b><br/><link href="{safe_href}">{safe_link_text}</link>',
#                     styles["BodyText"],
#                 )
#             )
#             story.append(Spacer(1, 8))
#         except Exception:
#             unavailable_count += 1

#     if unavailable_count:
#         story.append(Paragraph(f"{unavailable_count} video link(s) could not be generated.", styles["Italic"]))
#     return story
def _build_video_link_section(inspection: Inspection, styles):
    video_media = [
        media for media in (inspection.media or [])
        if not media.is_deleted and media.media_type == MediaType.VIDEO
    ]
    if not video_media:
        return []

    story = [Paragraph("Video Evidence Links (Click to open)", styles["Heading3"]), Spacer(1, 6)]
    unavailable_count = 0

    for index, media in enumerate(video_media, start=1):
        try:
            video_url = get_external_object_url(media.object_path)
            label = media.sub_area.name if media.sub_area else media.original_file_name
            safe_label = escape(label or f"Video {index}")
            safe_href = escape(video_url, {'"': "&quot;"})
            safe_link_text = escape(video_url)

            story.append(
                Paragraph(
                    # f'{index}. <b>{safe_label}</b><br/><link href="{safe_href}">{safe_link_text}</link>',
                    f'{index}. <link href="{safe_href}">{safe_label}</link>',
                    styles["BodyText"],
                )
            )
            story.append(Spacer(1, 8))
        except Exception as exc:
            unavailable_count += 1
            label = media.sub_area.name if media.sub_area else media.original_file_name
            safe_label = escape(label or f"Video {index}")
            safe_error = escape(str(exc))
            story.append(
                Paragraph(
                    f'{index}. <b>{safe_label}</b><br/>Link generation failed: {safe_error}',
                    styles["BodyText"],
                )
            )
            story.append(Spacer(1, 8))

    if unavailable_count:
        story.append(Paragraph(f"{unavailable_count} video link(s) could not be generated.", styles["Italic"]))

    return story

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
    styles = _configure_pdf_styles()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=28, bottomMargin=28)
    story = []
    story.append(_build_report_header(styles, "Inspection Report Summary"))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Inspection Metadata", styles["SectionTitle"]))
    story.append(_build_metadata_table(inspection, styles))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Entry-wise Findings", styles["SectionTitle"]))

    entries = db.query(InspectionEntry).filter_by(inspection_id=inspection.id, is_deleted=False).order_by(InspectionEntry.id).all()
    if entries:
        data = [[
            Paragraph("Entry", styles["TableHeader"]),
            Paragraph("Attribute", styles["TableHeader"]),
            Paragraph("Sub-area", styles["TableHeader"]),
            Paragraph("Grade", styles["TableHeader"]),
            Paragraph("Score", styles["TableHeader"]),
            Paragraph("Photo / Video", styles["TableHeader"]),
            Paragraph("Captured", styles["TableHeader"]),
            Paragraph("Remarks", styles["TableHeader"]),
        ]]
        for e in entries:
            photos, videos = _media_counts(db, e.id)
            captured = e.captured_at.strftime("%d-%m-%Y %H:%M") if e.captured_at else "-"
            gps = f"GPS {e.captured_latitude or '-'}, {e.captured_longitude or '-'} acc {e.gps_accuracy or '-'}m"
            data.append([
                _p(e.entry_no, styles["TableCellCenter"]),
                _p(e.attribute.name if e.attribute else e.attribute_id, styles["TableCell"]),
                _p(e.sub_area.name if e.sub_area else e.sub_area_id, styles["TableCell"]),
                _p(e.grade_code, styles["TableCellCenter"]),
                _p(f"{e.grade_percentage}%", styles["TableCellCenter"]),
                _p(f"P:{photos} V:{videos}", styles["TableCellCenter"]),
                _p(f"{captured}\n{gps}", styles["TableCell"]),
                _p(e.remarks or "-", styles["TableCell"]),
            ])
        table = Table(data, repeatRows=1, colWidths=[34, 78, 72, 44, 44, 58, 95, 110])
    else:
        data = [[
            Paragraph("Attribute", styles["TableHeader"]),
            Paragraph("Grade", styles["TableHeader"]),
            Paragraph("Score", styles["TableHeader"]),
            Paragraph("Remarks", styles["TableHeader"]),
        ]]
        for s in inspection.attribute_scores:
            data.append([
                _p(s.attribute.name if s.attribute else s.attribute_id, styles["TableCell"]),
                _p(s.grade_code, styles["TableCellCenter"]),
                _p(f"{s.grade_percentage}%", styles["TableCellCenter"]),
                _p(s.remarks or "-", styles["TableCell"]),
            ])
        if len(data) == 1:
            data.append([_p("No entry records", styles["TableCell"]), _p("-", styles["TableCellCenter"]), _p("-", styles["TableCellCenter"]), _p("-", styles["TableCell"])])
        table = Table(data, repeatRows=1, colWidths=[220, 70, 70, 175])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        ("TEXTCOLOR", (0, 0), (-1, 0), REPORT_TEXT),
        ("BOX", (0, 0), (-1, -1), 0.8, REPORT_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, REPORT_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, REPORT_ROW_ALT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    total_media = len([media for media in (inspection.media or []) if not media.is_deleted])
    total_photos = len([media for media in (inspection.media or []) if not media.is_deleted and media.media_type == MediaType.PHOTO])
    total_videos = len([media for media in (inspection.media or []) if not media.is_deleted and media.media_type == MediaType.VIDEO])
    story.append(Spacer(1, 16))
    story.append(Paragraph("Evidence Summary", styles["SectionTitle"]))
    story.append(_build_summary_table(total_media, total_photos, total_videos, styles))
    story.append(Spacer(1, 12))
    story.extend(_build_photo_preview_table(inspection, styles))
    if total_videos:
        story.append(Spacer(1, 12))
        story.extend(_build_video_link_section(inspection, styles))
    doc.build(story, onFirstPage=_draw_pdf_footer, onLaterPages=_draw_pdf_footer)
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
    styles = _configure_pdf_styles()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=22, leftMargin=22, topMargin=24, bottomMargin=20)
    story = [Paragraph("DMRC MCH KPI-6 Entry-wise Inspection Register", styles["SectionTitle"])]
    story.append(Paragraph(
        f"Filters: From <b>{_safe_text(from_date)}</b> To <b>{_safe_text(to_date)}</b> | "
        f"Station <b>{_safe_text(station_id, 'All')}</b> | Contract <b>{_safe_text(contract_id, 'All')}</b> | "
        f"Inspector <b>{_safe_text(submitted_by, 'All')}</b>",
        styles["Normal"],
    ))
    story.append(Spacer(1, 10))
    data = [[
        Paragraph("Inspection No", styles["TableHeader"]),
        Paragraph("Date", styles["TableHeader"]),
        Paragraph("Station", styles["TableHeader"]),
        Paragraph("Inspector", styles["TableHeader"]),
        Paragraph("Status", styles["TableHeader"]),
        Paragraph("Entry", styles["TableHeader"]),
        Paragraph("Attribute", styles["TableHeader"]),
        Paragraph("Sub-area", styles["TableHeader"]),
        Paragraph("Grade", styles["TableHeader"]),
        Paragraph("P / V", styles["TableHeader"]),
    ]]
    for i in inspections:
        entries = db.query(InspectionEntry).filter_by(inspection_id=i.id, is_deleted=False).order_by(InspectionEntry.id).all()
        if entries:
            for e in entries:
                photos, videos = _media_counts(db, e.id)
                data.append([
                    _p(i.inspection_no, styles["TableCell"]),
                    _p(i.inspection_date, styles["TableCellCenter"]),
                    _p(i.station.station_name if i.station else i.station_id, styles["TableCell"]),
                    _p(i.submitter.name if i.submitter else i.submitted_by, styles["TableCell"]),
                    _p(i.status.value, styles["TableCellCenter"]),
                    _p(e.entry_no, styles["TableCellCenter"]),
                    _p(e.attribute.name if e.attribute else e.attribute_id, styles["TableCell"]),
                    _p(e.sub_area.name if e.sub_area else e.sub_area_id, styles["TableCell"]),
                    _p(f"{e.grade_code} ({e.grade_percentage}%)", styles["TableCellCenter"]),
                    _p(f"{photos}/{videos}", styles["TableCellCenter"]),
                ])
        else:
            data.append([
                _p(i.inspection_no, styles["TableCell"]),
                _p(i.inspection_date, styles["TableCellCenter"]),
                _p(i.station.station_name if i.station else i.station_id, styles["TableCell"]),
                _p(i.submitter.name if i.submitter else i.submitted_by, styles["TableCell"]),
                _p(i.status.value, styles["TableCellCenter"]),
                _p("-", styles["TableCellCenter"]),
                _p("No entry records", styles["TableCell"]),
                _p("-", styles["TableCellCenter"]),
                _p(f"{_inspection_score(i)}%", styles["TableCellCenter"]),
                _p(str(len(i.media or [])), styles["TableCellCenter"]),
            ])
    if len(data) == 1:
        data.append([
            _p("No records", styles["TableCell"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
        ])
    table = Table(data, repeatRows=1, colWidths=[115, 58, 95, 95, 105, 48, 110, 105, 62, 35])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        ("TEXTCOLOR", (0, 0), (-1, 0), REPORT_TEXT),
        ("BOX", (0, 0), (-1, -1), 0.8, REPORT_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, REPORT_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, REPORT_ROW_ALT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    doc.build(story, onFirstPage=_draw_pdf_footer, onLaterPages=_draw_pdf_footer)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=inspection-register-entry-wise.pdf"})
