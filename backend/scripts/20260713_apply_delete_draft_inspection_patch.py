from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT
PROJECT = ROOT.parent


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding='utf-8')


def replace_once(content: str, old: str, new: str, label: str) -> str:
    if new in content:
        return content
    if old not in content:
        raise RuntimeError(f'Could not find expected block for {label}')
    return content.replace(old, new, 1)


def patch_inspections_endpoint() -> None:
    path = BACKEND / 'app' / 'api' / 'v1' / 'endpoints' / 'inspections.py'
    content = read(path)

    if 'InspectionWorkflowHistory,' not in content:
        content = replace_once(
            content,
            '    InspectionType,\n    MediaType,',
            '    InspectionType,\n    InspectionWorkflowHistory,\n    MediaType,',
            'InspectionWorkflowHistory import',
        )

    if 'ChemicalInspectionEntry' not in content:
        content = replace_once(
            content,
            'from app.models.kpi_chemical import InspectionKpiContext, KPI_6_CLEANLINESS, KPI_CHEMICALS',
            'from app.models.kpi_chemical import ChemicalInspectionEntry, InspectionKpiContext, KPI_6_CLEANLINESS, KPI_CHEMICALS',
            'ChemicalInspectionEntry import',
        )

    # Tell frontend explicitly that own draft rows can be deleted.
    if '"can_delete_draft": inspection.status == InspectionStatus.DRAFT' not in content:
        content = replace_once(
            content,
            '            "can_continue": inspection.status in ACTION_REQUIRED_STATUSES,\n',
            '            "can_continue": inspection.status in ACTION_REQUIRED_STATUSES,\n            "can_delete_draft": inspection.status == InspectionStatus.DRAFT,\n',
            'action required can_delete flag',
        )

    delete_endpoint = r'''

@router.delete("/{inspection_id}/draft")
def delete_draft_inspection(inspection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete an unsubmitted draft inspection owned by the logged-in field user.

    This is intentionally narrow:
    - only DRAFT inspections can be deleted;
    - only the original submitter can delete it;
    - only field inspector roles get this self-service delete option.

    Submitted / returned inspections remain part of the workflow trail and cannot be
    deleted from this endpoint.
    """

    inspection = db.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    if inspection.status != InspectionStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft inspections can be deleted. Submitted or returned inspections cannot be deleted.")

    if inspection.submitted_by != user.id:
        raise HTTPException(status_code=403, detail="You can delete only your own draft inspection.")

    role_code = user.role.code if user and user.role else None
    if role_code not in {RoleCode.STATION_MANAGER, RoleCode.EIT_MEMBER}:
        raise HTTPException(status_code=403, detail="Only SM/EIT users can delete their own draft inspections from Action Required.")

    deleted_summary = {
        "inspection_id": inspection.id,
        "inspection_no": inspection.inspection_no,
        "station_id": inspection.station_id,
        "contract_id": inspection.contract_id,
        "submitted_by": inspection.submitted_by,
        "status": inspection.status.value if getattr(inspection.status, "value", None) else str(inspection.status),
    }

    audit_log(
        db,
        actor=user,
        action="DRAFT_INSPECTION_DELETED_BY_SUBMITTER",
        entity_type="Inspection",
        entity_id=inspection.id,
        old_value=deleted_summary,
    )

    # Explicitly remove child rows first so databases without ON DELETE CASCADE do not
    # block deletion. Evidence objects already uploaded to MinIO are not reused by the
    # application after these database rows are removed.
    db.query(InspectionMedia).filter(InspectionMedia.inspection_id == inspection.id).delete(synchronize_session=False)
    db.query(InspectionEntry).filter(InspectionEntry.inspection_id == inspection.id).delete(synchronize_session=False)
    db.query(InspectionAttributeScore).filter(InspectionAttributeScore.inspection_id == inspection.id).delete(synchronize_session=False)
    db.query(InspectionSubAreaObservation).filter(InspectionSubAreaObservation.inspection_id == inspection.id).delete(synchronize_session=False)
    db.query(InspectionReview).filter(InspectionReview.inspection_id == inspection.id).delete(synchronize_session=False)
    db.query(InspectionWorkflowHistory).filter(InspectionWorkflowHistory.inspection_id == inspection.id).delete(synchronize_session=False)
    db.query(ChemicalInspectionEntry).filter(ChemicalInspectionEntry.inspection_id == inspection.id).delete(synchronize_session=False)
    db.query(InspectionKpiContext).filter(InspectionKpiContext.inspection_id == inspection.id).delete(synchronize_session=False)

    db.delete(inspection)
    db.commit()

    return {"message": "Draft inspection deleted successfully", **deleted_summary}
'''

    if '@router.delete("/{inspection_id}/draft")' not in content:
        anchor = '''@router.get("/{inspection_id}", response_model=InspectionOut)\ndef get_inspection'''
        if anchor not in content:
            raise RuntimeError('Could not find get_inspection anchor')
        content = content.replace(anchor, delete_endpoint + '\n\n' + anchor, 1)

    write(path, content)


def patch_action_required_view() -> None:
    path = PROJECT / 'frontend' / 'src' / 'views' / 'ActionRequiredView.vue'
    content = read(path)

    if 'success-box' not in content:
        content = replace_once(
            content,
            '''      <div v-if="loading" class="state-box">Loading action-required inspections...</div>\n''',
            '''      <div v-if="success" class="state-box success-box">\n        <strong>Done</strong>\n        <span>{{ success }}</span>\n      </div>\n      <div v-if="loading" class="state-box">Loading action-required inspections...</div>\n''',
            'success message block',
        )

    if 'deleteDraft(item)' not in content:
        content = replace_once(
            content,
            '''            <button class="btn btn-outline" type="button" @click="viewTrail(item)">View Trail</button>\n''',
            '''            <button class="btn btn-outline" type="button" @click="viewTrail(item)">View Trail</button>\n            <button\n              v-if="item.status === 'DRAFT' && item.can_delete_draft !== false"\n              class="btn btn-outline danger-button"\n              type="button"\n              :disabled="deletingId === item.id"\n              @click="deleteDraft(item)"\n            >\n              {{ deletingId === item.id ? 'Deleting...' : 'Delete Draft' }}\n            </button>\n''',
            'delete draft button',
        )

    if "const success = ref('')" not in content:
        content = replace_once(
            content,
            "const error = ref('')\nconst selectedItem = ref(null)\n",
            "const error = ref('')\nconst success = ref('')\nconst selectedItem = ref(null)\nconst deletingId = ref(null)\n",
            'success/deleting refs',
        )

    if 'async function deleteDraft(item)' not in content:
        delete_func = r'''
async function deleteDraft(item) {
  if (!item || item.status !== 'DRAFT') return
  const ok = window.confirm(
    `Delete draft inspection ${item.inspection_no}?\n\nThis will permanently remove the draft, its entries and uploaded evidence references. Submitted or returned inspections cannot be deleted.`
  )
  if (!ok) return

  deletingId.value = item.id
  error.value = ''
  success.value = ''
  try {
    await api.delete(`/inspections/${item.id}/draft`)
    success.value = `Draft inspection ${item.inspection_no} deleted successfully.`
    if (rows.value.length === 1 && pagination.page > 1) pagination.page -= 1
    await loadPage()
  } catch (e) {
    error.value = apiErrorText(e, 'Unable to delete draft inspection')
  } finally {
    deletingId.value = null
  }
}

'''
        content = replace_once(
            content,
            'function viewTrail(item) { selectedItem.value = item }\n\nfunction formatDate(value) {',
            'function viewTrail(item) { selectedItem.value = item }\n' + delete_func + 'function formatDate(value) {',
            'deleteDraft function',
        )

    if 'success.value = \'\'' not in content:
        # clear stale success when manually refreshing/loading after a failed request remains okay; keep message after delete.
        pass

    if '.success-box' not in content:
        content = replace_once(
            content,
            '.error-box { display: grid; gap: 6px; color: #991b1b; background: #fff1f2; border-color: #fecaca; }\n',
            '.error-box { display: grid; gap: 6px; color: #991b1b; background: #fff1f2; border-color: #fecaca; }\n.success-box { display: grid; gap: 6px; color: #166534; background: #f0fdf4; border-color: #bbf7d0; }\n',
            'success-box style',
        )

    if '.danger-button' not in content:
        content = replace_once(
            content,
            '.badge.red { background: #fee2e2; color: #991b1b; }\n',
            '.badge.red { background: #fee2e2; color: #991b1b; }\n.danger-button { border-color: #fecaca; color: #991b1b; background: #fff7f7; }\n.danger-button:hover:not(:disabled) { background: #fee2e2; }\n',
            'danger button style',
        )

    write(path, content)


def main() -> None:
    patch_inspections_endpoint()
    patch_action_required_view()
    print('Delete draft inspection patch applied successfully.')


if __name__ == '__main__':
    main()
