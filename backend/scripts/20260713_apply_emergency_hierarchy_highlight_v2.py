from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    file_path = ROOT / path
    file_path.write_text(content, encoding="utf-8")


def replace_once(content: str, old: str, new: str, *, label: str) -> str:
    if new in content:
        return content
    if old not in content:
        raise RuntimeError(f"Could not find expected block for {label}")
    return content.replace(old, new, 1)


def patch_reviews_endpoint() -> None:
    path = "backend/app/api/v1/endpoints/reviews.py"
    content = read(path)

    helper = '''
def _inspection_device_info(inspection: Inspection) -> dict:
    return inspection.device_info if isinstance(inspection.device_info, dict) else {}


def _is_emergency_inspection(inspection: Inspection) -> bool:
    return bool(_inspection_device_info(inspection).get("emergency_inspection"))


def _emergency_reason(inspection: Inspection) -> str | None:
    info = _inspection_device_info(inspection)
    reason = info.get("emergency_reason") or info.get("reason")
    if reason:
        return str(reason).strip()
    if _is_emergency_inspection(inspection) and inspection.remarks:
        remarks = str(inspection.remarks).strip()
        if remarks.lower().startswith("emergency inspection:"):
            return remarks.split(":", 1)[1].strip() or None
    return None


def _emergency_payload(inspection: Inspection) -> dict:
    info = _inspection_device_info(inspection)
    return {
        "is_emergency": _is_emergency_inspection(inspection),
        "emergency_reason": _emergency_reason(inspection),
        "emergency_started_by_user_id": info.get("emergency_started_by_user_id"),
        "normal_station_assignment_bypassed": bool(info.get("normal_station_assignment_bypassed")),
    }


'''
    content = replace_once(
        content,
        "def _review_payload(review: InspectionReview | None) -> dict | None:\n",
        helper + "def _review_payload(review: InspectionReview | None) -> dict | None:\n",
        label="reviews emergency helpers",
    )

    content = replace_once(
        content,
        '''    current_status = inspection.status.value if inspection.status else None
    submitter_name = inspection.submitter.name if inspection.submitter else None

    stages = [
''',
        '''    current_status = inspection.status.value if inspection.status else None
    submitter_name = inspection.submitter.name if inspection.submitter else None
    emergency = _emergency_payload(inspection)
    submitted_note = "Submitted for hierarchy review" if inspection.submitted_at else "Not submitted yet"
    if emergency["is_emergency"]:
        submitted_note = (
            f"EMERGENCY INSPECTION. Reason: {emergency['emergency_reason'] or 'Not provided'}. "
            + submitted_note
        )

    stages = [
''',
        label="reviews workflow emergency note variables",
    )

    content = replace_once(
        content,
        '            note="Submitted for hierarchy review" if inspection.submitted_at else "Not submitted yet",\n',
        '            note=submitted_note,\n',
        label="reviews submitted stage note",
    )

    content = replace_once(
        content,
        '        "workflow_tracker": _workflow_tracker(db, i),\n',
        '''        "is_emergency": _is_emergency_inspection(i),
        "emergency_reason": _emergency_reason(i),
        "emergency": _emergency_payload(i),
        "workflow_tracker": _workflow_tracker(db, i),
''',
        label="reviews row emergency fields",
    )

    content = replace_once(
        content,
        '        "reviews": [_review_payload(review) for review in reviews],\n',
        '''        "reviews": [_review_payload(review) for review in reviews],
        "emergency": emergency,
''',
        label="reviews tracker emergency field",
    )

    write(path, content)


def patch_reports_endpoint() -> None:
    path = "backend/app/api/v1/endpoints/reports.py"
    content = read(path)

    helper = '''
def _inspection_device_info(inspection: Inspection) -> dict:
    return inspection.device_info if isinstance(inspection.device_info, dict) else {}


def _is_emergency_inspection(inspection: Inspection) -> bool:
    return bool(_inspection_device_info(inspection).get("emergency_inspection"))


def _emergency_reason(inspection: Inspection) -> str | None:
    info = _inspection_device_info(inspection)
    reason = info.get("emergency_reason") or info.get("reason")
    if reason:
        return str(reason).strip()
    if _is_emergency_inspection(inspection) and inspection.remarks:
        remarks = str(inspection.remarks).strip()
        if remarks.lower().startswith("emergency inspection:"):
            return remarks.split(":", 1)[1].strip() or None
    return None


def _build_emergency_banner(inspection: Inspection, styles) -> list:
    if not _is_emergency_inspection(inspection):
        return []

    info = _inspection_device_info(inspection)
    reason = _emergency_reason(inspection) or "Not provided"
    bypass_text = "Yes" if info.get("normal_station_assignment_bypassed") else "No / assigned station"
    rows = [[
        Paragraph("EMERGENCY INSPECTION", styles["TableHeader"]),
        Paragraph(f"<b>Reason:</b> {_safe_text(reason)}<br/><b>Station assignment bypassed:</b> {_safe_text(bypass_text)}", styles["MetaValue"]),
    ]]
    table = Table(rows, colWidths=[150, 385])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7ed")),
        ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#f97316")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#fed7aa")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [Spacer(1, 10), table]


'''
    content = replace_once(
        content,
        "def _evidence_signature(media_id: int, expires_at: int) -> str:\n",
        helper + "def _evidence_signature(media_id: int, expires_at: int) -> str:\n",
        label="reports emergency helpers",
    )

    content = replace_once(
        content,
        '        "media_count": len(media),\n',
        '''        "media_count": len(media),
        "is_emergency": _is_emergency_inspection(i),
        "emergency_reason": _emergency_reason(i),
        "emergency": {
            "is_emergency": _is_emergency_inspection(i),
            "emergency_reason": _emergency_reason(i),
            "normal_station_assignment_bypassed": bool(_inspection_device_info(i).get("normal_station_assignment_bypassed")),
        },
''',
        label="reports search row emergency fields",
    )

    content = replace_once(
        content,
        '''    story.append(Paragraph("Inspection Metadata", styles["SectionTitle"]))
    story.append(_build_metadata_table(inspection, styles))
    story.append(Spacer(1, 14))
''',
        '''    story.append(Paragraph("Inspection Metadata", styles["SectionTitle"]))
    story.append(_build_metadata_table(inspection, styles))
    story.extend(_build_emergency_banner(inspection, styles))
    story.append(Spacer(1, 14))
''',
        label="reports inspection pdf emergency banner",
    )

    content = replace_once(
        content,
        '                    _p(_status_label(i.status.value), styles["TableCellCenter"]),\n',
        '                    _p(("EMERGENCY\\n" if _is_emergency_inspection(i) else "") + _status_label(i.status.value), styles["TableCellCenter"]),\n',
        label="reports register status emergency label",
    )

    content = replace_once(
        content,
        '                _p(i.status.value, styles["TableCellCenter"]),\n',
        '                _p(("EMERGENCY\\n" if _is_emergency_inspection(i) else "") + _status_label(i.status.value), styles["TableCellCenter"]),\n',
        label="reports register no-entry emergency status label",
    )

    write(path, content)


def patch_review_queue_view() -> None:
    path = "frontend/src/views/ReviewQueueView.vue"
    content = read(path)

    content = replace_once(
        content,
        '              <td><strong>{{ i.inspection_no }}</strong><br /><span class="muted small-text">{{ shortType(i.inspection_type) }}</span></td>\n',
        '''              <td>
                <strong>{{ i.inspection_no }}</strong><br />
                <span class="muted small-text">{{ shortType(i.inspection_type) }}</span>
                <span v-if="isEmergency(i)" class="badge red emergency-mini-badge">Emergency</span>
              </td>
''',
        label="review desktop emergency inspection number",
    )

    content = replace_once(
        content,
        '              <td>{{ i.station_name || i.station_id }}<br /><span class="muted small-text">{{ i.contract_code || \'-\' }}</span></td>\n',
        '''              <td>
                {{ i.station_name || i.station_id }}<br />
                <span class="muted small-text">{{ i.contract_code || '-' }}</span>
                <p v-if="isEmergency(i)" class="emergency-reason-line">Reason: {{ emergencyReason(i) }}</p>
              </td>
''',
        label="review desktop emergency reason",
    )

    content = replace_once(
        content,
        '            <span class="badge" :class="statusClass(i.status)">{{ statusLabel(i.status) }}</span>\n',
        '''            <span class="badge" :class="statusClass(i.status)">{{ statusLabel(i.status) }}</span>
            <span v-if="isEmergency(i)" class="badge red">Emergency</span>
''',
        label="review mobile emergency badge",
    )

    content = replace_once(
        content,
        '            <span>Score</span><b>{{ displayPercent(i.score) }}</b>\n',
        '''            <span>Score</span><b>{{ displayPercent(i.score) }}</b>
            <template v-if="isEmergency(i)">
              <span>Emergency reason</span><b class="emergency-text">{{ emergencyReason(i) }}</b>
            </template>
''',
        label="review mobile emergency reason",
    )

    content = replace_once(
        content,
        '        <div class="tracker-status-summary">\n',
        '''        <div v-if="isEmergency(selectedTrackerRow)" class="emergency-alert">
          <strong>Emergency Inspection</strong>
          <span>Reason: {{ emergencyReason(selectedTrackerRow) }}</span>
        </div>

        <div class="tracker-status-summary">
''',
        label="review tracker emergency alert",
    )

    content = replace_once(
        content,
        '''        <div class="review-rule-box">
          <strong>{{ reviewRuleTitle(reviewModal.item) }}</strong>
          <span>{{ reviewRuleText(reviewModal.item) }}</span>
        </div>

        <div class="review-form-grid">
''',
        '''        <div class="review-rule-box">
          <strong>{{ reviewRuleTitle(reviewModal.item) }}</strong>
          <span>{{ reviewRuleText(reviewModal.item) }}</span>
        </div>

        <div v-if="isEmergency(reviewModal.item)" class="emergency-alert review-emergency-alert">
          <strong>Emergency Inspection</strong>
          <span>Reason: {{ emergencyReason(reviewModal.item) }}</span>
          <small>Keep this context in your review remarks before forwarding / final decision.</small>
        </div>

        <div class="review-form-grid">
''',
        label="review modal emergency alert",
    )

    content = replace_once(
        content,
        '''function displayPercent(value) {
  if (value === null || value === undefined || value === '') return '-'
  return `${Number(value).toFixed(2).replace(/\\.00$/, '')}%`
}
''',
        '''function displayPercent(value) {
  if (value === null || value === undefined || value === '') return '-'
  return `${Number(value).toFixed(2).replace(/\\.00$/, '')}%`
}
function isEmergency(item) {
  return Boolean(item?.is_emergency || item?.emergency?.is_emergency)
}
function emergencyReason(item) {
  return item?.emergency_reason || item?.emergency?.emergency_reason || 'Reason not provided'
}
''',
        label="review emergency functions",
    )

    review_emergency_css = '''.emergency-mini-badge { display: inline-flex; margin-top: 6px; width: fit-content; }
.emergency-reason-line { margin: 6px 0 0; color: #991b1b; font-size: 11px; font-weight: 900; line-height: 1.35; }
.emergency-alert { display: grid; gap: 4px; margin: 14px 0; border: 1px solid #fed7aa; background: #fff7ed; color: #9a3412; border-radius: 16px; padding: 12px 14px; line-height: 1.4; }
.emergency-alert strong { color: #9a3412; }
.emergency-alert small { color: #7c2d12; font-weight: 800; }
.emergency-text { color: #991b1b !important; }
'''
    if '.emergency-mini-badge' not in content:
        if '@media (max-width: 760px)' in content:
            content = content.replace('@media (max-width: 760px)', review_emergency_css + '\n@media (max-width: 760px)', 1)
        elif '</style>' in content:
            content = content.replace('</style>', review_emergency_css + '\n</style>', 1)
        else:
            raise RuntimeError('Could not find style insertion point for review emergency styles')

    write(path, content)


def patch_reports_view() -> None:
    path = "frontend/src/views/ReportsView.vue"
    content = read(path)

    content = replace_once(
        content,
        '              <td><strong>{{ r.inspection_no }}</strong></td><td>{{ formatDate(r.inspection_date) }}</td><td>{{ r.station_name || \'-\' }}</td><td>{{ r.contract_code || \'-\' }}</td><td>{{ r.submitted_by_name || \'-\' }}</td><td><span class="badge">{{ shortType(r.inspection_type) }}</span></td><td><strong>{{ displayPercent(r.score) }}</strong></td>\n',
        '''              <td><strong>{{ r.inspection_no }}</strong><br /><span v-if="isEmergency(r)" class="badge red emergency-mini-badge">Emergency</span></td><td>{{ formatDate(r.inspection_date) }}</td><td>{{ r.station_name || '-' }}<p v-if="isEmergency(r)" class="emergency-reason-line">Reason: {{ emergencyReason(r) }}</p></td><td>{{ r.contract_code || '-' }}</td><td>{{ r.submitted_by_name || '-' }}</td><td><span class="badge">{{ shortType(r.inspection_type) }}</span></td><td><strong>{{ displayPercent(r.score) }}</strong></td>
''',
        label="reports desktop emergency row",
    )

    content = replace_once(
        content,
        '<div class="mobile-record-top"><strong>{{ r.inspection_no }}</strong><span class="badge" :class="statusClass(r.status)">{{ statusLabel(r.status) }}</span></div>\n',
        '<div class="mobile-record-top"><strong>{{ r.inspection_no }}</strong><span class="badge" :class="statusClass(r.status)">{{ statusLabel(r.status) }}</span><span v-if="isEmergency(r)" class="badge red">Emergency</span></div>\n',
        label="reports mobile emergency badge",
    )

    content = replace_once(
        content,
        '<div class="mobile-record-grid"><span>Date</span><b>{{ formatDate(r.inspection_date) }}</b><span>Station</span><b>{{ r.station_name || \'-\' }}</b><span>Contract</span><b>{{ r.contract_code || \'-\' }}</b><span>Inspector</span><b>{{ r.submitted_by_name || \'-\' }}</b><span>Type</span><b>{{ shortType(r.inspection_type) }}</b><span>Score</span><b>{{ displayPercent(r.score) }}</b></div>\n',
        '<div class="mobile-record-grid"><span>Date</span><b>{{ formatDate(r.inspection_date) }}</b><span>Station</span><b>{{ r.station_name || \'-\' }}</b><template v-if="isEmergency(r)"><span>Emergency reason</span><b class="emergency-text">{{ emergencyReason(r) }}</b></template><span>Contract</span><b>{{ r.contract_code || \'-\' }}</b><span>Inspector</span><b>{{ r.submitted_by_name || \'-\' }}</b><span>Type</span><b>{{ shortType(r.inspection_type) }}</b><span>Score</span><b>{{ displayPercent(r.score) }}</b></div>\n',
        label="reports mobile emergency reason",
    )

    content = replace_once(
        content,
        '<div class="tracker-status-summary"><span class="label">Current status</span><span class="badge" :class="statusClass(selectedTrackerRow.status)">{{ statusLabel(selectedTrackerRow.status) }}</span></div><div class="workflow-tracker modal-tracker">',
        '<div v-if="isEmergency(selectedTrackerRow)" class="emergency-alert"><strong>Emergency Inspection</strong><span>Reason: {{ emergencyReason(selectedTrackerRow) }}</span></div><div class="tracker-status-summary"><span class="label">Current status</span><span class="badge" :class="statusClass(selectedTrackerRow.status)">{{ statusLabel(selectedTrackerRow.status) }}</span></div><div class="workflow-tracker modal-tracker">',
        label="reports tracker emergency alert",
    )

    content = replace_once(
        content,
        "function formatDateTime(value){ if(!value) return 'Pending'; if(/^\\d{4}-\\d{2}-\\d{2}$/.test(String(value))) return formatDate(value); return new Date(value).toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short'}) } function displayPercent(value){ if(value===null||value===undefined||value==='') return '-'; return `${Number(value).toFixed(2).replace(/\\.00$/,'')}%` }\n",
        "function formatDateTime(value){ if(!value) return 'Pending'; if(/^\\d{4}-\\d{2}-\\d{2}$/.test(String(value))) return formatDate(value); return new Date(value).toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short'}) } function displayPercent(value){ if(value===null||value===undefined||value==='') return '-'; return `${Number(value).toFixed(2).replace(/\\.00$/,'')}%` }\nfunction isEmergency(item){ return Boolean(item?.is_emergency || item?.emergency?.is_emergency) }\nfunction emergencyReason(item){ return item?.emergency_reason || item?.emergency?.emergency_reason || 'Reason not provided' }\n",
        label="reports emergency functions",
    )

    reports_emergency_css = ".emergency-mini-badge{display:inline-flex;margin-top:6px;width:fit-content}.emergency-reason-line{margin:6px 0 0;color:#991b1b;font-size:11px;font-weight:900;line-height:1.35}.emergency-alert{display:grid;gap:4px;margin:14px 0;border:1px solid #fed7aa;background:#fff7ed;color:#9a3412;border-radius:16px;padding:12px 14px;line-height:1.4}.emergency-alert strong{color:#9a3412}.emergency-text{color:#991b1b!important}\n"
    if '.emergency-mini-badge' not in content:
        if '@media' in content:
            content = content.replace('@media', reports_emergency_css + '@media', 1)
        elif '</style>' in content:
            content = content.replace('</style>', reports_emergency_css + '</style>', 1)
        else:
            raise RuntimeError('Could not find style insertion point for reports emergency styles')

    write(path, content)


def main() -> None:
    patch_reviews_endpoint()
    patch_reports_endpoint()
    patch_review_queue_view()
    patch_reports_view()
    print("Emergency inspection hierarchy highlight V2 patch applied successfully.")


if __name__ == "__main__":
    main()
