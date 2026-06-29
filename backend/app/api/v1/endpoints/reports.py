from datetime import date
from io import BytesIO
import hashlib
import hmac
import time
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as PlatypusImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import apply_inspection_scope, require_inspection_access
from app.models.all_models import (
    Inspection,
    InspectionEntry,
    InspectionMedia,
    InspectionReview,
    InspectionStatus,
    InspectionType,
    MediaType,
    User,
)
from app.models.kpi_chemical import ChemicalInspectionEntry, InspectionKpiContext, KPI_CHEMICALS
from app.services.media_service import download_bytes

router = APIRouter()

EVIDENCE_LINK_TTL_SECONDS = 7 * 24 * 60 * 60

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


def _evidence_signature(media_id: int, expires_at: int) -> str:
    message = f"{media_id}:{expires_at}".encode("utf-8")
    secret = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _create_evidence_token(media_id: int) -> str:
    expires_at = int(time.time()) + EVIDENCE_LINK_TTL_SECONDS
    signature = _evidence_signature(media_id, expires_at)
    return f"{expires_at}.{signature}"


def _verify_evidence_token(media_id: int, token: str) -> None:
    try:
        expires_raw, signature = token.split(".", 1)
        expires_at = int(expires_raw)
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid evidence link")

    if expires_at < int(time.time()):
        raise HTTPException(status_code=403, detail="Evidence link has expired")

    expected_signature = _evidence_signature(media_id, expires_at)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=403, detail="Invalid evidence link")


def _public_app_base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host or request.headers.get("host")
    proto = forwarded_proto or request.url.scheme

    if host and not host.startswith(("api", "mch_api")):
        return f"{proto}://{host}".rstrip("/")

    configured_origin = (settings.FRONTEND_ORIGIN or "").strip().rstrip("/")
    if configured_origin:
        return configured_origin

    return str(request.base_url).rstrip("/")


def _evidence_url(request: Request, media: InspectionMedia) -> str:
    base_url = _public_app_base_url(request)
    api_prefix = settings.API_PREFIX.rstrip("/")
    token = _create_evidence_token(media.id)
    return f"{base_url}{api_prefix}/reports/evidence/{media.id}?token={token}"


def _inline_filename(filename: str | None, fallback: str = "evidence") -> str:
    safe = (filename or fallback).replace("\\", "_").replace("/", "_").replace('"', "")
    return safe or fallback


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
            [Paragraph(title_markup, styles["HeaderTitle"])],
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
            Paragraph(_safe_text(_status_label(inspection.status.value)), styles["MetaValue"]),
            Paragraph("Inspection Score", styles["MetaLabel"]),
            Paragraph(f"<b>{_inspection_score(inspection)}%</b>", styles["MetaValue"]),
        ],
    ]
    table = Table(metadata, colWidths=[78, 190, 78, 189])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), REPORT_SURFACE),
        ("BACKGROUND", (2, 0), (2, -1), REPORT_SURFACE),
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


def _query_inspections(
    db: Session,
    user: User,
    from_date=None,
    to_date=None,
    station_id=None,
    contract_id=None,
    submitted_by=None,
    inspection_type=None,
    status=None,
):
    q = apply_inspection_scope(
        db.query(Inspection).order_by(Inspection.inspection_date.desc(), Inspection.id.desc()),
        db,
        user,
    )
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
    return q.order_by(Inspection.inspection_date.desc(), Inspection.id.desc())


def _row(i: Inspection) -> dict:
    entries = [e for e in getattr(i, "entries", []) if not getattr(e, "is_deleted", False)]
    media = [m for m in getattr(i, "media", []) if not getattr(m, "is_deleted", False)]
    return {
        "id": i.id,
        "inspection_no": i.inspection_no,
        "inspection_date": i.inspection_date.isoformat() if i.inspection_date else None,
        "inspection_type": i.inspection_type.value if i.inspection_type else None,
        "status": i.status.value if i.status else None,
        "station_id": i.station_id,
        "station_name": i.station.station_name if i.station else None,
        "contract_id": i.contract_id,
        "contract_code": i.contract.contract_code if i.contract else None,
        "submitted_by": i.submitted_by,
        "submitted_by_name": i.submitter.name if i.submitter else None,
        "score": _inspection_score(i),
        "entry_count": len(entries),
        "media_count": len(media),
    }


def _paginate_query(query, page: int = 1, size: int = 20) -> dict:
    """Return a stable server-side pagination payload for report/search screens."""
    page = max(1, int(page or 1))
    size = min(100, max(1, int(size or 20)))

    total = query.count()
    pages = (total + size - 1) // size if total else 0
    items = query.offset((page - 1) * size).limit(size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_previous": page > 1,
        "has_next": page < pages,
    }


def _media_counts(db: Session, entry_id: int) -> tuple[int, int]:
    """Count non-deleted photo/video evidence attached to a specific inspection entry."""
    media = (
        db.query(InspectionMedia)
        .filter(
            InspectionMedia.inspection_entry_id == entry_id,
            InspectionMedia.is_deleted.is_(False),
        )
        .all()
    )
    photos = sum(1 for item in media if item.media_type == MediaType.PHOTO)
    videos = sum(1 for item in media if item.media_type == MediaType.VIDEO)
    return photos, videos


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


def _build_photo_preview_table(inspection: Inspection, styles, request: Request):
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
            image_url = _evidence_url(request, media)
            label = media.sub_area.name if media.sub_area else media.original_file_name
            safe_label = escape(label or "Photo")
            safe_href = escape(image_url, {'"': "&quot;"})

            cells.append([
                thumbnail,
                Spacer(1, 4),
                Paragraph(f"<b>{safe_label}</b>", styles["BodyText"]),
                Spacer(1, 2),
                Paragraph(f'<link href="{safe_href}">Open full-resolution image</link>', styles["BodyText"]),
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


def _build_video_link_section(inspection: Inspection, styles, request: Request):
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
            video_url = _evidence_url(request, media)
            label = media.sub_area.name if media.sub_area else media.original_file_name
            safe_label = escape(label or f"Video {index}")
            safe_href = escape(video_url, {'"': "&quot;"})

            story.append(
                Paragraph(
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



def _review_action_label(action_value: str | None) -> str:
    labels = {
        "COMMENT": "Comment",
        "RETURN_FOR_CLARIFICATION": "Returned for clarification",
        "RECOMMEND_PENALTY": "Forwarded / recommended",
        "APPROVE": "Approved",
        "REJECT": "Rejected",
        "SEND_TO_GM": "Forwarded to GM/Ops",
        "GM_REVIEW": "Reviewed by GM/Ops",
    }
    return labels.get(action_value or "", str(action_value or "-").replace("_", " ").title())


def _review_level_label(level: str | None) -> str:
    labels = {
        "LINE_MANAGER": "Line Manager",
        "DGM": "DGM",
        "GM": "GM/Ops",
    }
    return labels.get(level or "", str(level or "-").replace("_", " ").title())


def _format_review_datetime(value) -> str:
    return value.strftime("%d-%m-%Y %H:%M") if value else "-"


def _build_approval_remarks_table(db: Session, inspection: Inspection, styles):
    """Build the hierarchy approval / forwarding remarks trail for the inspection PDF."""
    reviews = (
        db.query(InspectionReview)
        .filter(InspectionReview.inspection_id == inspection.id)
        .order_by(InspectionReview.reviewed_at.asc(), InspectionReview.id.asc())
        .all()
    )

    if not reviews:
        return []

    data = [[
        Paragraph("Level", styles["TableHeader"]),
        Paragraph("Action", styles["TableHeader"]),
        Paragraph("By", styles["TableHeader"]),
        Paragraph("When", styles["TableHeader"]),
        Paragraph("Remarks", styles["TableHeader"]),
    ]]

    for review in reviews:
        action_value = review.action.value if getattr(review.action, "value", None) else str(review.action or "")
        reviewer_name = review.reviewer.name if review.reviewer else f"User #{review.reviewer_id}"
        reviewer_role = review.reviewer_role or "-"
        by_text = f"{reviewer_name}\n{reviewer_role}"
        data.append([
            _p(_review_level_label(review.review_level), styles["TableCellCenter"]),
            _p(_review_action_label(action_value), styles["TableCell"]),
            _p(by_text, styles["TableCell"]),
            _p(_format_review_datetime(review.reviewed_at), styles["TableCellCenter"]),
            _p(review.comments or "-", styles["TableCell"]),
        ])

    table = Table(data, repeatRows=1, colWidths=[72, 112, 118, 88, 145])
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

    return [
        Spacer(1, 16),
        Paragraph("Approval / Forwarding Remarks", styles["SectionTitle"]),
        table,
    ]



def _inspection_kpi_category(db: Session, inspection_id: int) -> str:
    ctx = db.query(InspectionKpiContext).filter_by(inspection_id=inspection_id).first()
    return ctx.kpi_category if ctx else "KPI_6_CLEANLINESS"


def _chemical_summary(entries: list[ChemicalInspectionEntry]) -> dict:
    required_total = sum(float(row.required_quantity or 0) for row in entries if not row.is_deleted)
    actual_total = sum(float(row.actual_quantity or 0) for row in entries if not row.is_deleted)
    actual_capped_total = sum(min(float(row.actual_quantity or 0), float(row.required_quantity or 0)) for row in entries if not row.is_deleted)
    shortfall_total = sum(float(row.shortfall_quantity or 0) for row in entries if not row.is_deleted)
    score = 100 if required_total == 0 else round(actual_capped_total / required_total * 100, 2)
    return {
        "required_total": round(required_total, 2),
        "actual_total": round(actual_total, 2),
        "shortfall_total": round(shortfall_total, 2),
        "score_percent": score,
        "below_threshold": score < 90,
    }


def _build_chemical_findings_table(db: Session, inspection: Inspection, styles):
    entries = (
        db.query(ChemicalInspectionEntry)
        .filter(ChemicalInspectionEntry.inspection_id == inspection.id, ChemicalInspectionEntry.is_deleted.is_(False))
        .order_by(ChemicalInspectionEntry.id)
        .all()
    )
    summary = _chemical_summary(entries)
    story = [Paragraph("KPI Chemicals & Consumables Findings", styles["SectionTitle"])]
    story.append(Paragraph(
        f"Overall availability score: <b>{summary['score_percent']}%</b> | Required total: <b>{summary['required_total']}</b> | Actual total: <b>{summary['actual_total']}</b> | Shortfall: <b>{summary['shortfall_total']}</b>",
        styles["Normal"],
    ))
    story.append(Spacer(1, 8))
    data = [[
        Paragraph("Chemical", styles["TableHeader"]),
        Paragraph("Required", styles["TableHeader"]),
        Paragraph("Actual", styles["TableHeader"]),
        Paragraph("Difference", styles["TableHeader"]),
        Paragraph("Shortfall", styles["TableHeader"]),
        Paragraph("Availability", styles["TableHeader"]),
        Paragraph("Remarks", styles["TableHeader"]),
    ]]
    if entries:
        for row in entries:
            chemical = row.chemical
            difference = round((row.actual_quantity or 0) - (row.required_quantity or 0), 2)
            unit = chemical.unit if chemical else ""
            data.append([
                _p(chemical.name if chemical else row.chemical_id, styles["TableCell"]),
                _p(f"{row.required_quantity} {unit}", styles["TableCellCenter"]),
                _p(f"{row.actual_quantity} {unit}", styles["TableCellCenter"]),
                _p(f"{difference} {unit}", styles["TableCellCenter"]),
                _p(f"{row.shortfall_quantity} {unit}", styles["TableCellCenter"]),
                _p(f"{row.availability_percent}%", styles["TableCellCenter"]),
                _p(row.remarks or "-", styles["TableCell"]),
            ])
    else:
        data.append([
            _p("No chemical entries", styles["TableCell"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCellCenter"]),
            _p("-", styles["TableCell"]),
        ])
    table = Table(data, repeatRows=1, colWidths=[115, 62, 62, 62, 62, 72, 100])
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
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "KPI rule reference: Chemicals & Consumables score is shortfall based; penalty applies if pass percentage is below 90% during billing cycle.",
        styles["Italic"],
    ))
    return story


def _status_label(status_value: str | None) -> str:
    labels = {
        "UNDER_LINE_MANAGER_REVIEW": "SUBMITTED TO LINE MANAGER",
        "LINE_MANAGER_RECOMMENDED": "APPROVED BY LINE MANAGER",
        "DGM_APPROVED": "APPROVED BY DGM",
        "DRAFT": "DRAFT",
    }
    return labels.get(status_value, status_value or "-")


@router.get("/inspections/search")
def search_inspection_reports(
    from_date: date | None = None,
    to_date: date | None = None,
    station_id: int | None = None,
    contract_id: int | None = None,
    submitted_by: int | None = None,
    inspection_type: InspectionType | None = None,
    status: InspectionStatus | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = _query_inspections(db, user, from_date, to_date, station_id, contract_id, submitted_by, inspection_type, status)
    data = _paginate_query(query, page, size)
    data["items"] = [_row(i) for i in data["items"]]
    return data


@router.get("/inspection/{inspection_id}/pdf")
def inspection_pdf(inspection_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    require_inspection_access(db, user, inspection)

    buffer = BytesIO()
    styles = _configure_pdf_styles()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=28, bottomMargin=28)
    story = []
    story.append(_build_report_header(styles, "Inspection Report Summary"))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Inspection Metadata", styles["SectionTitle"]))
    story.append(_build_metadata_table(inspection, styles))
    story.append(Spacer(1, 14))
    if _inspection_kpi_category(db, inspection.id) == KPI_CHEMICALS:
        story.extend(_build_chemical_findings_table(db, inspection, styles))
    else:
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
                data.append([
                    _p("No entry records", styles["TableCell"]),
                    _p("-", styles["TableCellCenter"]),
                    _p("-", styles["TableCellCenter"]),
                    _p("-", styles["TableCell"]),
                ])
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
    story.extend(_build_approval_remarks_table(db, inspection, styles))

    total_media = len([media for media in (inspection.media or []) if not media.is_deleted])
    total_photos = len([media for media in (inspection.media or []) if not media.is_deleted and media.media_type == MediaType.PHOTO])
    total_videos = len([media for media in (inspection.media or []) if not media.is_deleted and media.media_type == MediaType.VIDEO])
    story.append(Spacer(1, 16))
    story.append(Paragraph("Evidence Summary", styles["SectionTitle"]))
    story.append(_build_summary_table(total_media, total_photos, total_videos, styles))
    story.append(Spacer(1, 12))
    story.extend(_build_photo_preview_table(inspection, styles, request))
    if total_videos:
        story.append(Spacer(1, 12))
        story.extend(_build_video_link_section(inspection, styles, request))

    doc.build(story, onFirstPage=_draw_pdf_footer, onLaterPages=_draw_pdf_footer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={inspection.inspection_no}.pdf"},
    )


@router.get("/evidence/{media_id}")
def open_report_evidence(media_id: int, token: str, db: Session = Depends(get_db)):
    _verify_evidence_token(media_id, token)

    media = db.get(InspectionMedia, media_id)
    if not media or media.is_deleted:
        raise HTTPException(status_code=404, detail="Evidence file not found")

    data = download_bytes(media.object_path)
    filename = _inline_filename(media.original_file_name, f"evidence-{media.id}")
    return Response(
        content=data,
        media_type=media.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


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
    inspections = _query_inspections(db, user, from_date, to_date, station_id, contract_id, submitted_by, inspection_type, status).limit(5000).all()
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
                    _p(_status_label(i.status.value), styles["TableCellCenter"]),
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
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=inspection-register.pdf"},
    )
