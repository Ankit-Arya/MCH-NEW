from pathlib import Path
import shutil
import sys

PATCH_MARKER_BACKEND = "# LM TRANSFER WITH REPLACEMENT PATCH"
PATCH_MARKER_FRONTEND = "<!-- LM TRANSFER WITH REPLACEMENT PATCH -->"


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
    backup_path = path.with_suffix(path.suffix + ".bak.lm-transfer-reassignment")
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
        raise RuntimeError("Missing file: " + str(path))
    content = read_text(path)
    if PATCH_MARKER_BACKEND in content:
        print("Backend already patched:", path)
        return

    backup(path)

    if "from pydantic import BaseModel" not in content:
        content = replace_once(
            content,
            "from fastapi import APIRouter, Depends, HTTPException, status\n",
            "from fastapi import APIRouter, Depends, HTTPException, status\nfrom pydantic import BaseModel\n",
            "backend BaseModel import",
        )

    constants_block = "STATION_ONLY_ROLES = {RoleCode.STATION_MANAGER, RoleCode.EIT_MEMBER}\n"
    constants_replacement = '''STATION_ONLY_ROLES = {RoleCode.STATION_MANAGER, RoleCode.EIT_MEMBER}
LINE_MANAGER_ROLES = {RoleCode.AM_MGR_LINE, RoleCode.AM_MGR_HK}
DGM_ROLES = {RoleCode.DGM_LINE, RoleCode.DGM_HK}
FIELD_INSPECTOR_ROLES = {RoleCode.STATION_MANAGER, RoleCode.EIT_MEMBER}


class LineManagerTransferUpdate(BaseModel):
    """Transfer one LM to a new DGM and hand over that LM's SM/EIT children.

    This is different from normal reporting-link editing. A person transfer should move
    only the LM. The SM/EIT team that previously reported to that LM is reassigned to
    a replacement LM under the old DGM.
    """

    transferred_lm_user_id: int
    new_dgm_user_id: int
    replacement_lm_user_id: int
    relation_type: str = REPORTING_RELATION

'''
    content = replace_once(content, constants_block, constants_replacement, "backend transfer constants/model")

    helper_marker = "def _replace_station_access(db: Session, payload: StationAccessUpdate, actor: User) -> dict[str, Any]:\n"
    helper_code = r'''
# LM TRANSFER WITH REPLACEMENT PATCH
def _active_reporting_parent_rows(db: Session, subordinate_user_id: int, relation_type: str = REPORTING_RELATION):
    return (
        db.query(UserSupervisorAccess)
        .options(joinedload(UserSupervisorAccess.supervisor).joinedload(User.role))
        .filter(
            UserSupervisorAccess.subordinate_user_id == subordinate_user_id,
            UserSupervisorAccess.relation_type == relation_type,
            UserSupervisorAccess.is_active.is_(True),
        )
        .all()
    )


def _active_reporting_child_rows(db: Session, supervisor_user_id: int, relation_type: str = REPORTING_RELATION):
    return (
        db.query(UserSupervisorAccess)
        .options(joinedload(UserSupervisorAccess.subordinate).joinedload(User.role))
        .filter(
            UserSupervisorAccess.supervisor_user_id == supervisor_user_id,
            UserSupervisorAccess.relation_type == relation_type,
            UserSupervisorAccess.is_active.is_(True),
        )
        .all()
    )


def _get_or_create_reporting_link(
    db: Session,
    *,
    supervisor_user_id: int,
    subordinate_user_id: int,
    relation_type: str,
) -> UserSupervisorAccess:
    row = (
        db.query(UserSupervisorAccess)
        .filter(
            UserSupervisorAccess.supervisor_user_id == supervisor_user_id,
            UserSupervisorAccess.subordinate_user_id == subordinate_user_id,
            UserSupervisorAccess.relation_type == relation_type,
        )
        .first()
    )
    if row:
        row.is_active = True
        return row

    row = UserSupervisorAccess(
        supervisor_user_id=supervisor_user_id,
        subordinate_user_id=subordinate_user_id,
        relation_type=relation_type,
        is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def _transfer_line_manager_with_replacement(
    db: Session,
    *,
    payload: LineManagerTransferUpdate,
    actor: User,
) -> dict[str, Any]:
    relation_type = payload.relation_type or REPORTING_RELATION
    transferred_lm = _ensure_user(db, int(payload.transferred_lm_user_id))
    new_dgm = _ensure_user(db, int(payload.new_dgm_user_id))
    replacement_lm = _ensure_user(db, int(payload.replacement_lm_user_id))

    if _role_code(transferred_lm) not in LINE_MANAGER_ROLES:
        raise HTTPException(status_code=422, detail="Transferred user must be a Line Manager / HK Manager")
    if _role_code(new_dgm) not in DGM_ROLES:
        raise HTTPException(status_code=422, detail="New supervisor must be a DGM Line / DGM HK")
    if _role_code(replacement_lm) not in LINE_MANAGER_ROLES:
        raise HTTPException(status_code=422, detail="Replacement user must be a Line Manager / HK Manager")
    if transferred_lm.id == replacement_lm.id:
        raise HTTPException(status_code=422, detail="Replacement LM cannot be the same person being transferred")
    if transferred_lm.id == new_dgm.id or replacement_lm.id == new_dgm.id:
        raise HTTPException(status_code=422, detail="Invalid transfer selection")

    parent_rows = _active_reporting_parent_rows(db, transferred_lm.id, relation_type)
    old_dgm_rows = [row for row in parent_rows if _role_code(row.supervisor) in DGM_ROLES]
    if len(old_dgm_rows) != 1:
        raise HTTPException(
            status_code=422,
            detail="Selected LM must currently have exactly one active DGM supervisor before transfer.",
        )

    old_dgm = old_dgm_rows[0].supervisor
    if old_dgm.id == new_dgm.id:
        raise HTTPException(status_code=422, detail="Selected LM is already under this DGM")

    replacement_parent_rows = _active_reporting_parent_rows(db, replacement_lm.id, relation_type)
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
    for row in parent_rows:
        row.is_active = False
    _ensure_no_reporting_cycle(db, new_dgm.id, transferred_lm.id)
    _get_or_create_reporting_link(
        db,
        supervisor_user_id=new_dgm.id,
        subordinate_user_id=transferred_lm.id,
        relation_type=relation_type,
    )

    # 2. Hand over only SM/EIT children from the transferred LM to replacement LM.
    child_rows = _active_reporting_child_rows(db, transferred_lm.id, relation_type)
    field_child_rows = [
        row for row in child_rows
        if row.subordinate is not None and _role_code(row.subordinate) in FIELD_INSPECTOR_ROLES
    ]
    moved_children = []
    for row in field_child_rows:
        subordinate_id = row.subordinate_user_id
        subordinate = row.subordinate
        _ensure_no_reporting_cycle(db, replacement_lm.id, subordinate_id)

        # Disable the old LM -> SM/EIT link and any other active parent link to keep single-parent rule.
        for parent_row in _active_reporting_parent_rows(db, subordinate_id, relation_type):
            if parent_row.supervisor_user_id != replacement_lm.id:
                parent_row.is_active = False

        _get_or_create_reporting_link(
            db,
            supervisor_user_id=replacement_lm.id,
            subordinate_user_id=subordinate_id,
            relation_type=relation_type,
        )
        moved_children.append({
            "id": subordinate_id,
            "name": subordinate.name if subordinate else None,
            "role": subordinate.role.code.value if subordinate and subordinate.role else None,
        })

    untouched_children = [
        {
            "id": row.subordinate_user_id,
            "name": row.subordinate.name if row.subordinate else None,
            "role": row.subordinate.role.code.value if row.subordinate and row.subordinate.role else None,
        }
        for row in child_rows
        if row.subordinate is not None and _role_code(row.subordinate) not in FIELD_INSPECTOR_ROLES
    ]

    audit_log(
        db,
        actor=actor,
        action="ACCESS_LM_TRANSFERRED_WITH_REPLACEMENT",
        entity_type="User",
        entity_id=transferred_lm.id,
        new_value={
            "transferred_lm_user_id": transferred_lm.id,
            "transferred_lm_name": transferred_lm.name,
            "old_dgm_user_id": old_dgm.id,
            "old_dgm_name": old_dgm.name,
            "new_dgm_user_id": new_dgm.id,
            "new_dgm_name": new_dgm.name,
            "replacement_lm_user_id": replacement_lm.id,
            "replacement_lm_name": replacement_lm.name,
            "moved_sm_eit_count": len(moved_children),
            "moved_sm_eit_users": moved_children,
            "untouched_non_field_children": untouched_children,
            "relation_type": relation_type,
            "rule": "Transfer person only; reassign previous SM/EIT team to replacement LM",
        },
    )

    return {
        "message": (
            f"{transferred_lm.name} transferred from {old_dgm.name} to {new_dgm.name}. "
            f"{len(moved_children)} SM/EIT user(s) reassigned to {replacement_lm.name}."
        ),
        "transferred_lm_user_id": transferred_lm.id,
        "old_dgm_user_id": old_dgm.id,
        "new_dgm_user_id": new_dgm.id,
        "replacement_lm_user_id": replacement_lm.id,
        "moved_sm_eit_count": len(moved_children),
        "moved_sm_eit_users": moved_children,
        "untouched_non_field_children": untouched_children,
    }


'''
    content = replace_once(content, helper_marker, helper_code + helper_marker, "backend transfer helpers")

    endpoint_marker = '''@router.put("/reporting-links")
def set_reporting_links(payload: ReportingAccessUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
'''
    endpoint_code = '''@router.post("/transfer-line-manager")
def transfer_line_manager(
    payload: LineManagerTransferUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Transfer one LM to another DGM without dragging SM/EIT children with the person.

    Flow:
    - old DGM -> transferred LM is disabled
    - new DGM -> transferred LM is enabled
    - transferred LM -> SM/EIT links are disabled
    - replacement LM -> those SM/EIT links are enabled
    """

    _require_manage(user)
    result = _transfer_line_manager_with_replacement(db, payload=payload, actor=user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate reporting mapping during LM transfer. Please refresh hierarchy and try again.",
        ) from exc
    return result


'''
    content = replace_once(content, endpoint_marker, endpoint_code + endpoint_marker, "backend transfer endpoint")

    write_text(path, content)
    print("Patched backend:", path)


def patch_frontend(root):
    path = root / "frontend" / "src" / "views" / "AccessControlView.vue"
    if not path.exists():
        raise RuntimeError("Missing file: " + str(path))
    content = read_text(path)
    if PATCH_MARKER_FRONTEND in content:
        print("Frontend already patched:", path)
        return

    backup(path)

    section_marker = '''    <section class="card section-gap" v-if="!loading && !loadError">
      <div class="card-title tree-title-row">
'''
    transfer_section = '''    <!-- LM TRANSFER WITH REPLACEMENT PATCH -->
    <section id="lm-transfer-editor" class="card section-gap transfer-card" v-if="!loading && !loadError">
      <div class="card-title">
        <div>
          <h2>Transfer Line Manager</h2>
          <p class="muted small-text">
            Use this when one LM is transferred to another DGM. Only the LM moves. The SM/EIT team below that LM is handed over to a replacement LM under the old DGM.
          </p>
        </div>
      </div>

      <div class="transfer-grid">
        <label class="form-field">
          <span class="label">LM being transferred</span>
          <select class="input" v-model.number="transferLmId">
            <option :value="0">Select current LM</option>
            <option v-for="u in transferLmUsers" :key="u.id" :value="u.id">
              {{ u.name }} - {{ u.username }} - {{ roleLabel(u.role) }}
            </option>
          </select>
        </label>

        <label class="form-field">
          <span class="label">New DGM supervisor</span>
          <select class="input" v-model.number="transferNewDgmId">
            <option :value="0">Select new DGM</option>
            <option v-for="u in transferDgmUsers" :key="u.id" :value="u.id">
              {{ u.name }} - {{ u.username }} - {{ roleLabel(u.role) }}
            </option>
          </select>
        </label>

        <label class="form-field">
          <span class="label">Replacement LM for previous SM/EIT team</span>
          <select class="input" v-model.number="transferReplacementLmId">
            <option :value="0">Select replacement LM</option>
            <option v-for="u in transferReplacementLmCandidates" :key="u.id" :value="u.id">
              {{ u.name }} - {{ u.username }} - {{ roleLabel(u.role) }}
            </option>
          </select>
        </label>
      </div>

      <div class="transfer-preview">
        <div><span>Current DGM</span><strong>{{ transferOldDgm ? `${transferOldDgm.name} - ${roleLabel(transferOldDgm.role)}` : 'Select an LM to detect current DGM' }}</strong></div>
        <div><span>SM/EIT team to hand over</span><strong>{{ transferChildUsers.length }} user{{ transferChildUsers.length === 1 ? '' : 's' }}</strong></div>
        <p v-if="transferChildUsers.length">
          {{ transferChildUsers.map((u) => u.name).slice(0, 6).join(', ') }}<template v-if="transferChildUsers.length > 6"> and {{ transferChildUsers.length - 6 }} more</template>
        </p>
        <p v-else class="muted small-text">No active SM/EIT child users are currently mapped under this LM.</p>
      </div>

      <div class="transfer-warning">
        <strong>Practical transfer rule</strong>
        <span>Do not use normal hierarchy mapping for LM transfer. Normal mapping changes reporting links only. This transfer action moves the LM and reassigns the old SM/EIT team to the replacement LM in one transaction.</span>
      </div>

      <button class="btn btn-primary full-button" :disabled="!canTransferLm || savingTransfer" @click="transferLineManager">
        {{ savingTransfer ? 'Transferring...' : 'Transfer LM and reassign previous team' }}
      </button>
    </section>

'''
    content = replace_once(content, section_marker, transfer_section + section_marker, "frontend transfer section")

    refs_marker = '''const selectedSupervisorId = ref(0)
const selectedSubordinateIds = ref([])
const savingHierarchy = ref(false)
const expandedNodeIds = ref(new Set())
'''
    refs_replacement = '''const selectedSupervisorId = ref(0)
const selectedSubordinateIds = ref([])
const savingHierarchy = ref(false)
const transferLmId = ref(0)
const transferNewDgmId = ref(0)
const transferReplacementLmId = ref(0)
const savingTransfer = ref(false)
const expandedNodeIds = ref(new Set())
'''
    content = replace_once(content, refs_marker, refs_replacement, "frontend transfer refs")

    computed_marker = '''const selectedAccessUser = computed(() => userById.value[Number(selectedAccessUserId.value)])
const selectedSupervisor = computed(() => userById.value[Number(selectedSupervisorId.value)])
'''
    computed_replacement = '''const selectedAccessUser = computed(() => userById.value[Number(selectedAccessUserId.value)])
const selectedSupervisor = computed(() => userById.value[Number(selectedSupervisorId.value)])

// LM TRANSFER WITH REPLACEMENT PATCH
const transferLmUsers = computed(() => activeUsers.value.filter((u) => isLm(u.role)))
const transferDgmUsers = computed(() => activeUsers.value.filter((u) => isDgm(u.role)))
const transferOldDgm = computed(() => {
  const parents = parentMap.value.get(Number(transferLmId.value)) || []
  return parents.find((user) => isDgm(user.role)) || null
})
const transferChildUsers = computed(() => {
  const children = childMap.value.get(Number(transferLmId.value)) || []
  return children.filter((user) => ['STATION_MANAGER', 'EIT_MEMBER'].includes(user.role))
})
const transferReplacementLmCandidates = computed(() => {
  const oldDgm = transferOldDgm.value
  return transferLmUsers.value.filter((user) => {
    if (Number(user.id) === Number(transferLmId.value)) return false
    if (!oldDgm) return true
    const parents = parentMap.value.get(Number(user.id)) || []
    return parents.some((parent) => Number(parent.id) === Number(oldDgm.id))
  })
})
const canTransferLm = computed(() => Boolean(
  transferLmId.value &&
  transferNewDgmId.value &&
  transferReplacementLmId.value &&
  Number(transferLmId.value) !== Number(transferReplacementLmId.value)
))
'''
    content = replace_once(content, computed_marker, computed_replacement, "frontend transfer computed")

    function_marker = "function plainHierarchyLines() {\n"
    transfer_function = r'''// LM TRANSFER WITH REPLACEMENT PATCH
async function transferLineManager() {
  clearMessages()

  if (!canTransferLm.value) {
    error.value = 'Select LM being transferred, new DGM, and replacement LM.'
    return
  }
  if (!transferOldDgm.value) {
    error.value = 'Selected LM must currently be under one DGM before transfer.'
    return
  }
  if (Number(transferOldDgm.value.id) === Number(transferNewDgmId.value)) {
    error.value = 'Selected LM is already under this DGM.'
    return
  }

  const lm = userById.value[Number(transferLmId.value)]
  const newDgm = userById.value[Number(transferNewDgmId.value)]
  const replacement = userById.value[Number(transferReplacementLmId.value)]
  const count = transferChildUsers.value.length
  const message = [
    `Transfer ${lm?.name || 'selected LM'} from ${transferOldDgm.value?.name || 'current DGM'} to ${newDgm?.name || 'new DGM'}?`,
    `${count} SM/EIT user${count === 1 ? '' : 's'} currently under this LM will be reassigned to ${replacement?.name || 'replacement LM'}.`,
    'This avoids moving the whole station team along with the transferred LM.'
  ].join('\n\n')

  if (!window.confirm(message)) return

  savingTransfer.value = true
  try {
    const { data } = await api.post('/access-control/transfer-line-manager', {
      transferred_lm_user_id: Number(transferLmId.value),
      new_dgm_user_id: Number(transferNewDgmId.value),
      replacement_lm_user_id: Number(transferReplacementLmId.value),
      relation_type: 'REPORTING'
    })
    success.value = data?.message || 'Line Manager transferred and previous team reassigned.'
    transferLmId.value = 0
    transferNewDgmId.value = 0
    transferReplacementLmId.value = 0
    await load()
  } catch (e) {
    error.value = formatApiError(e, 'Unable to transfer Line Manager')
  } finally {
    savingTransfer.value = false
  }
}

'''
    content = replace_once(content, function_marker, transfer_function + function_marker, "frontend transfer function")

    css_marker = "@media (max-width: 860px) {\n"
    css_code = '''/* LM TRANSFER WITH REPLACEMENT PATCH */
.transfer-card { border-color: #bfdbfe; background: linear-gradient(135deg, #fff 0%, #f8fbff 100%); }
.transfer-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.form-field { display: grid; gap: 6px; }
.transfer-preview { display: grid; gap: 8px; margin-top: 12px; border: 1px solid #dbeafe; background: #eff6ff; border-radius: 18px; padding: 12px 14px; color: #1e3a8a; }
.transfer-preview > div { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.transfer-preview span { font-weight: 900; color: #64748b; }
.transfer-preview strong { color: #0f172a; }
.transfer-preview p { margin: 0; color: #334155; font-weight: 700; line-height: 1.45; }
.transfer-warning { display: grid; gap: 4px; margin: 12px 0; border: 1px solid #fde68a; background: #fffbeb; color: #78350f; border-radius: 18px; padding: 12px 14px; line-height: 1.45; }
.transfer-warning strong { color: #92400e; }

'''
    if css_marker in content:
        content = replace_once(content, css_marker, css_code + css_marker, "frontend transfer styles")
    else:
        content = replace_once(content, "</style>", css_code + "</style>", "frontend transfer styles fallback")

    mobile_css_marker = "  .action-buttons { min-width: 0; }\n"
    mobile_css_replacement = "  .action-buttons { min-width: 0; }\n  .transfer-grid { grid-template-columns: 1fr; }\n  .transfer-preview > div { display: grid; }\n"
    if mobile_css_marker in content:
        content = replace_once(content, mobile_css_marker, mobile_css_replacement, "frontend transfer mobile styles")

    write_text(path, content)
    print("Patched frontend:", path)


def main():
    root = find_project_root()
    print("Project root:", root)
    patch_backend(root)
    patch_frontend(root)
    print("LM transfer reassignment patch applied successfully.")
    print("Rebuild with: docker compose up -d --build api frontend")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Patch failed:", exc)
        sys.exit(1)
