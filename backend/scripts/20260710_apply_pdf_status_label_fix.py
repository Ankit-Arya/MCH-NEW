
# Patch report/PDF wording for corrected approval hierarchy.
# Run from project root after copying this patch:
#     python backend/scripts/20260710_apply_pdf_status_label_fix.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "reports.py"

text = REPORTS.read_text(encoding="utf-8")
original = text

replacements = {
    '\"RECOMMEND_PENALTY\": \"Forwarded /Recommended\",': '\"RECOMMEND_PENALTY\": \"Forwarded to DGM\",',
    '\"APPROVE\": \"Approved\",': '\"APPROVE\": \"Final approved by GM/Ops\",',
    '\"REJECT\": \"Rejected\",': '\"REJECT\": \"Final rejected by GM/Ops\",',
    '\"UNDER_LINE_MANAGER_REVIEW\": \"SUBMITTED TO LINE MANAGER\",': '\"UNDER_LINE_MANAGER_REVIEW\": \"SUBMITTED TO LM/AM\",',
    '\"LINE_MANAGER_RECOMMENDED\": \"APPROVED BY LINE MANAGER\",': '\"LINE_MANAGER_RECOMMENDED\": \"FORWARDED BY LM/AM TO DGM\",',
    '\"DGM_APPROVED\": \"APPROVED BY DGM\",': '\"DGM_APPROVED\": \"FINAL APPROVED BY GM/OPS\",',
    '\"DGM_REJECTED\": \"REJECTED BY DGM\",': '\"DGM_REJECTED\": \"FINAL REJECTED BY GM/OPS\",',
    '\"GM_REVIEW_REQUIRED\": \"SENT TO GM/OPS\",': '\"GM_REVIEW_REQUIRED\": \"FORWARDED BY DGM TO GM/OPS\",',
}
for old, new in replacements.items():
    text = text.replace(old, new)

needle = '        "DGM_APPROVED": "FINAL APPROVED BY GM/OPS",\n        "DRAFT": "DRAFT",'
if needle in text and '"DGM_REJECTED": "FINAL REJECTED BY GM/OPS"' not in text:
    text = text.replace(
        needle,
        '        "DGM_APPROVED": "FINAL APPROVED BY GM/OPS",\n        "DGM_REJECTED": "FINAL REJECTED BY GM/OPS",\n        "GM_REVIEW_REQUIRED": "FORWARDED BY DGM TO GM/OPS",\n        "GM_REVIEWED": "REVIEWED BY GM/OPS",\n        "DRAFT": "DRAFT",'
    )

if text == original:
    print("No reports.py label changes were needed or expected patterns were not found.")
else:
    backup = REPORTS.with_suffix(REPORTS.suffix + ".bak-approval-hierarchy")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
    REPORTS.write_text(text, encoding="utf-8")
    print(f"Updated PDF/report labels in {REPORTS}")
    print(f"Backup saved at {backup}")
