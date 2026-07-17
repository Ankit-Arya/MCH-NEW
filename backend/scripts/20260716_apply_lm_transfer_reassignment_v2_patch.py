from pathlib import Path
import shutil
import sys

PATCH_MARKER = "# LM TRANSFER REPLACEMENT ANY ACTIVE LM V2"
FRONTEND_MARKER = "// LM TRANSFER REPLACEMENT ANY ACTIVE LM V2"


def find_project_root():
    here = Path.cwd().resolve()
    candidates = [here] + list(here.parents)
    for candidate in candidates:
        if (candidate / "backend" / "app").exists() and (candidate / "frontend" / "src").exists():
            return candidate
    raise RuntimeError("Project root not found. Run this script from mch-inspection-platform root.")


def read_text(path):
    with open(str(path), "r", encoding="utf-8") as handle:
        return handle.read()


def write_text(path, content):
    with open(str(path), "w", encoding="utf-8", newline="") as handle:
        handle.write(content)


def backup(path):
    backup_path = path.with_suffix(path.suffix + ".bak.lm-transfer-v2")
    if not backup_path.exists():
        shutil.copy2(str(path), str(backup_path))
    return backup_path


def replace_once(content, old, new, label):
    if old not in content:
        raise RuntimeError("Could not find expected block for " + label)
    return content.replace(old, new, 1)


def patch_backend(root):
    path = root / "backend" / "app" / "api" / "v1" / "endpoints" / "access_control.py"
    if not path.exists():
        raise RuntimeError("Missing backend file: " + str(path))

    content = read_text(path)
    if PATCH_MARKER in content:
        print("Backend already has V2 transfer logic:", path)
        return

    if "LineManagerTransferUpdate" not in content or "_transfer_line_manager_with_replacement" not in content:
        raise RuntimeError(
            "LM transfer V1 patch is not present in backend. Apply mch_lm_transfer_reassignment_patch first, then run this V2 patch."
        )

    backup(path)

    old_block = '''    replacement_parent_rows = _active_reporting_parent_rows(db, replacement_lm.id, relation_type)
    replacement_under_old_dgm = any(row.supervisor_user_id == old_dgm.id for row in replacement_parent_rows)
    if not replacement_under_old_dgm:
        raise HTTPException(
            status_code=422,
            detail=(
                "Replacement LM must be an active LM under the old DGM so the previous station team "
                "stays in the same DGM hierarchy."
            ),
        )

    # 1. Move only the LM under the new DGM.
'''

    new_block = '''    # LM TRANSFER REPLACEMENT ANY ACTIVE LM V2
    # Replacement LM may be any active LM except the transferred LM. If that replacement
    # is not already under the old/current DGM, place the replacement under old DGM first
    # so the previous SM/EIT team remains inside the old DGM hierarchy.
    replacement_parent_rows = _active_reporting_parent_rows(db, replacement_lm.id, relation_type)
    replacement_old_active_dgm_parents = [
        row for row in replacement_parent_rows
        if row.supervisor is not None and _role_code(row.supervisor) in DGM_ROLES
    ]
    replacement_previous_dgm_parents = [
        {
            "id": row.supervisor_user_id,
            "name": row.supervisor.name if row.supervisor else None,
            "role": row.supervisor.role.code.value if row.supervisor and row.supervisor.role else None,
        }
        for row in replacement_old_active_dgm_parents
    ]
    replacement_under_old_dgm = any(row.supervisor_user_id == old_dgm.id for row in replacement_old_active_dgm_parents)
    replacement_lm_moved_to_old_dgm = False

    if not replacement_under_old_dgm:
        _ensure_no_reporting_cycle(db, old_dgm.id, replacement_lm.id)
        for row in replacement_old_active_dgm_parents:
            row.is_active = False
        _get_or_create_reporting_link(
            db,
            supervisor_user_id=old_dgm.id,
            subordinate_user_id=replacement_lm.id,
            relation_type=relation_type,
        )
        replacement_lm_moved_to_old_dgm = True

    # 1. Move only the LM under the new DGM.
'''
    content = replace_once(content, old_block, new_block, "backend replacement-LM validation block")

    audit_old = '''            "replacement_lm_user_id": replacement_lm.id,
            "replacement_lm_name": replacement_lm.name,
            "moved_sm_eit_count": len(moved_children),
'''
    audit_new = '''            "replacement_lm_user_id": replacement_lm.id,
            "replacement_lm_name": replacement_lm.name,
            "replacement_lm_auto_mapped_to_old_dgm": replacement_lm_moved_to_old_dgm,
            "replacement_lm_previous_dgm_parents": replacement_previous_dgm_parents,
            "moved_sm_eit_count": len(moved_children),
'''
    if audit_old in content:
        content = replace_once(content, audit_old, audit_new, "backend audit payload")

    return_old = '''        "replacement_lm_user_id": replacement_lm.id,
        "moved_sm_eit_count": len(moved_children),
'''
    return_new = '''        "replacement_lm_user_id": replacement_lm.id,
        "replacement_lm_auto_mapped_to_old_dgm": replacement_lm_moved_to_old_dgm,
        "replacement_lm_previous_dgm_parents": replacement_previous_dgm_parents,
        "moved_sm_eit_count": len(moved_children),
'''
    if return_old in content:
        content = replace_once(content, return_old, return_new, "backend response payload")

    write_text(path, content)
    print("Patched backend transfer logic:", path)


def patch_frontend(root):
    path = root / "frontend" / "src" / "views" / "AccessControlView.vue"
    if not path.exists():
        raise RuntimeError("Missing frontend file: " + str(path))

    content = read_text(path)
    if FRONTEND_MARKER in content:
        print("Frontend already has V2 transfer logic:", path)
        return

    if "transferReplacementLmCandidates" not in content or "transferLineManager" not in content:
        raise RuntimeError(
            "LM transfer V1 patch is not present in frontend. Apply mch_lm_transfer_reassignment_patch first, then run this V2 patch."
        )

    backup(path)

    old_computed = '''const transferReplacementLmCandidates = computed(() => {
  const oldDgm = transferOldDgm.value
  return transferLmUsers.value.filter((user) => {
    if (Number(user.id) === Number(transferLmId.value)) return false
    if (!oldDgm) return true
    const parents = parentMap.value.get(Number(user.id)) || []
    return parents.some((parent) => Number(parent.id) === Number(oldDgm.id))
  })
})
const canTransferLm = computed(() => Boolean(
'''

    new_computed = '''// LM TRANSFER REPLACEMENT ANY ACTIVE LM V2
const transferReplacementLmCandidates = computed(() => transferLmUsers.value.filter((user) => Number(user.id) !== Number(transferLmId.value)))
const transferReplacementLmIsOutsideOldDgm = computed(() => {
  const oldDgm = transferOldDgm.value
  const replacementId = Number(transferReplacementLmId.value || 0)
  if (!oldDgm || !replacementId) return false
  const parents = parentMap.value.get(replacementId) || []
  return !parents.some((parent) => Number(parent.id) === Number(oldDgm.id))
})
const transferReplacementPlacementText = computed(() => {
  const replacement = userById.value[Number(transferReplacementLmId.value || 0)]
  if (!replacement) return 'Select a replacement LM'
  if (!transferOldDgm.value) return 'Current DGM not detected yet'
  if (transferReplacementLmIsOutsideOldDgm.value) {
    return `${replacement.name} will be mapped under ${transferOldDgm.value.name} before handover`
  }
  return `${replacement.name} is already under ${transferOldDgm.value.name}`
})
const canTransferLm = computed(() => Boolean(
'''
    content = replace_once(content, old_computed, new_computed, "frontend replacement candidate computed")

    old_preview = '''        <div><span>Current DGM</span><strong>{{ transferOldDgm ? `${transferOldDgm.name} - ${roleLabel(transferOldDgm.role)}` : 'Select an LM to detect current DGM' }}</strong></div>
        <div><span>SM/EIT team to hand over</span><strong>{{ transferChildUsers.length }} user{{ transferChildUsers.length === 1 ? '' : 's' }}</strong></div>
'''
    new_preview = '''        <div><span>Current DGM</span><strong>{{ transferOldDgm ? `${transferOldDgm.name} - ${roleLabel(transferOldDgm.role)}` : 'Select an LM to detect current DGM' }}</strong></div>
        <div><span>Replacement placement</span><strong>{{ transferReplacementPlacementText }}</strong></div>
        <div><span>SM/EIT team to hand over</span><strong>{{ transferChildUsers.length }} user{{ transferChildUsers.length === 1 ? '' : 's' }}</strong></div>
'''
    if old_preview in content:
        content = replace_once(content, old_preview, new_preview, "frontend transfer preview")

    old_message = '''  const replacement = userById.value[Number(transferReplacementLmId.value)]
  const count = transferChildUsers.value.length
  const message = [
    `Transfer ${lm?.name || 'selected LM'} from ${transferOldDgm.value?.name || 'current DGM'} to ${newDgm?.name || 'new DGM'}?`,
    `${count} SM/EIT user${count === 1 ? '' : 's'} currently under this LM will be reassigned to ${replacement?.name || 'replacement LM'}.`,
    'This avoids moving the whole station team along with the transferred LM.'
  ].join('\n\n')
'''
    new_message = '''  const replacement = userById.value[Number(transferReplacementLmId.value)]
  const count = transferChildUsers.value.length
  const placementNote = transferReplacementLmIsOutsideOldDgm.value
    ? `${replacement?.name || 'Replacement LM'} is not currently under ${transferOldDgm.value?.name || 'old DGM'}, so the system will first map the replacement LM under the old DGM.`
    : `${replacement?.name || 'Replacement LM'} is already under ${transferOldDgm.value?.name || 'old DGM'}.`
  const message = [
    `Transfer ${lm?.name || 'selected LM'} from ${transferOldDgm.value?.name || 'current DGM'} to ${newDgm?.name || 'new DGM'}?`,
    placementNote,
    `${count} SM/EIT user${count === 1 ? '' : 's'} currently under this LM will be reassigned to ${replacement?.name || 'replacement LM'}.`,
    'This avoids moving the whole station team along with the transferred LM.'
  ].join('\n\n')
'''
    if old_message in content:
        content = replace_once(content, old_message, new_message, "frontend confirmation message")

    write_text(path, content)
    print("Patched frontend transfer candidates:", path)


def main():
    root = find_project_root()
    print("Project root:", root)
    patch_backend(root)
    patch_frontend(root)
    print("LM transfer reassignment V2 patch applied successfully.")
    print("Rebuild with: docker compose up -d --build api frontend")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Patch failed:", exc)
        sys.exit(1)
