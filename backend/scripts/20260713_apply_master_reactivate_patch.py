from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
FRONTEND_ROOT = PROJECT_ROOT / "frontend"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Could not find expected block for {label}. File may already be changed or differs from expected version.")
    return text.replace(old, new, 1)


def insert_after(text: str, marker: str, addition: str, label: str) -> str:
    if addition.strip() in text:
        return text
    if marker not in text:
        raise SystemExit(f"Could not find insertion marker for {label}.")
    return text.replace(marker, marker + addition, 1)


def patch_master_backend() -> None:
    path = BACKEND_ROOT / "app" / "api" / "v1" / "endpoints" / "master.py"
    text = path.read_text(encoding="utf-8")

    deactivate_block = '''def _deactivate(db: Session, user: User, model: Type[Any], obj_id: int, entity_type: str) -> dict[str, Any]:
    _require_manage(user)
    obj = _get_or_404(db, model, obj_id)
    if not hasattr(obj, "is_active"):
        raise HTTPException(status_code=400, detail="This master data cannot be deactivated")
    old_value = _as_dict(obj)
    obj.is_active = False
    db.flush()
    audit_log(db, actor=user, action=f"MASTER_{entity_type}_DEACTIVATED", entity_type=entity_type, entity_id=obj.id, old_value=old_value, new_value=_as_dict(obj))
    _commit_or_409(db)
    return {"message": f"{entity_type} deactivated", "id": obj_id}
'''
    activate_block = deactivate_block + '''

def _activate(db: Session, user: User, model: Type[Any], obj_id: int, entity_type: str) -> dict[str, Any]:
    _require_manage(user)
    obj = _get_or_404(db, model, obj_id)
    if not hasattr(obj, "is_active"):
        raise HTTPException(status_code=400, detail="This master data cannot be activated")
    old_value = _as_dict(obj)
    obj.is_active = True
    db.flush()
    audit_log(db, actor=user, action=f"MASTER_{entity_type}_ACTIVATED", entity_type=entity_type, entity_id=obj.id, old_value=old_value, new_value=_as_dict(obj))
    _commit_or_409(db)
    return {"message": f"{entity_type} activated", "id": obj_id}
'''
    if "def _activate(" not in text:
        text = replace_once(text, deactivate_block, activate_block, "master _activate helper")

    endpoint_insertions = [
        (
'''@router.delete("/lines/{line_id}")
def deactivate_line(line_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, Line, line_id, "LINE")
''',
'''

@router.put("/lines/{line_id}/activate")
def activate_line(line_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, Line, line_id, "LINE")
''',
"line activate endpoint",
        ),
        (
'''@router.delete("/contractors/{contractor_id}")
def deactivate_contractor(contractor_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, Contractor, contractor_id, "CONTRACTOR")
''',
'''

@router.put("/contractors/{contractor_id}/activate")
def activate_contractor(contractor_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, Contractor, contractor_id, "CONTRACTOR")
''',
"contractor activate endpoint",
        ),
        (
'''@router.delete("/stations/{station_id}")
def deactivate_station(station_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, Station, station_id, "STATION")
''',
'''

@router.put("/stations/{station_id}/activate")
def activate_station(station_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, Station, station_id, "STATION")
''',
"station activate endpoint",
        ),
        (
'''@router.delete("/contracts/{contract_id}")
def deactivate_contract(contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, Contract, contract_id, "CONTRACT")
''',
'''

@router.put("/contracts/{contract_id}/activate")
def activate_contract(contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, Contract, contract_id, "CONTRACT")
''',
"contract activate endpoint",
        ),
        (
'''@router.delete("/inspection-attributes/{attribute_id}")
def deactivate_inspection_attribute(attribute_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, InspectionAttribute, attribute_id, "INSPECTION_ATTRIBUTE")
''',
'''

@router.put("/inspection-attributes/{attribute_id}/activate")
def activate_inspection_attribute(attribute_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, InspectionAttribute, attribute_id, "INSPECTION_ATTRIBUTE")
''',
"inspection attribute activate endpoint",
        ),
        (
'''@router.delete("/inspection-sub-areas/{sub_area_id}")
def deactivate_inspection_sub_area(sub_area_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, InspectionSubArea, sub_area_id, "INSPECTION_SUB_AREA")
''',
'''

@router.put("/inspection-sub-areas/{sub_area_id}/activate")
def activate_inspection_sub_area(sub_area_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, InspectionSubArea, sub_area_id, "INSPECTION_SUB_AREA")
''',
"inspection sub area activate endpoint",
        ),
        (
'''@router.delete("/grading-schemes/{scheme_id}")
def deactivate_grading_scheme(scheme_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _deactivate(db, user, GradingScheme, scheme_id, "GRADING_SCHEME")
''',
'''

@router.put("/grading-schemes/{scheme_id}/activate")
def activate_grading_scheme(scheme_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _activate(db, user, GradingScheme, scheme_id, "GRADING_SCHEME")
''',
"grading scheme activate endpoint",
        ),
    ]

    for marker, addition, label in endpoint_insertions:
        text = insert_after(text, marker, addition, label)

    path.write_text(text, encoding="utf-8")


def patch_master_frontend() -> None:
    path = FRONTEND_ROOT / "src" / "views" / "MasterDataView.vue"
    text = path.read_text(encoding="utf-8")

    text = insert_after(
        text,
'''              <input
                class="input"
                v-model.trim="searchQuery"
                :placeholder="`Search ${activeSection.label.toLowerCase()}`"
              />
''',
'''              <select class="input status-select" v-model="recordStatusFilter">
                <option value="ALL">All status</option>
                <option value="ACTIVE">Active only</option>
                <option value="INACTIVE">Inactive only</option>
              </select>
''',
        "master status filter select",
    )

    text = insert_after(
        text,
'''                @edit="editCurrent"
                @deactivate="deactivateCurrent"
''',
'''                @activate="activateCurrent"
''',
        "master table activate event",
    )

    text = insert_after(
        text,
'''                    @edit="editGradingScheme"
                    @deactivate="id => deactivate('/master/grading-schemes', id)"
''',
'''                    @activate="id => activate('/master/grading-schemes', id)"
''',
        "grading scheme activate event",
    )

    text = replace_once(
        text,
'''  emits: ['edit', 'deactivate'],
''',
'''  emits: ['edit', 'deactivate', 'activate'],
''',
        "MasterTable emits activate",
    )

    old_actions = '''                h('button', {
                  class: ['btn', 'btn-sm', 'btn-outline', 'danger-action'],
                  type: 'button',
                  disabled: row.is_active === false,
                  onClick: () => row.is_active === false ? null : emit('deactivate', row.id)
                }, row.is_active === false ? 'Inactive' : 'Deactivate')
'''
    new_actions = '''                row.is_active === false
                  ? h('button', {
                    class: ['btn', 'btn-sm', 'btn-outline', 'activate-action'],
                    type: 'button',
                    onClick: () => emit('activate', row.id)
                  }, 'Activate')
                  : h('button', {
                    class: ['btn', 'btn-sm', 'btn-outline', 'danger-action'],
                    type: 'button',
                    onClick: () => emit('deactivate', row.id)
                  }, 'Deactivate')
'''
    if old_actions in text:
        text = replace_once(text, old_actions, new_actions, "MasterTable active/inactive actions")
    elif "activate-action" not in text:
        raise SystemExit("Could not patch MasterTable actions.")

    text = insert_after(
        text,
'''const activeTab = ref('lines')
const searchQuery = ref('')
''',
'''const recordStatusFilter = ref('ALL')
''',
        "recordStatusFilter ref",
    )

    text = replace_once(
        text,
'''const filteredRows = computed(() => filterRows(activeRows.value, activeColumns.value))
const filteredGradingSchemes = computed(() => filterRows(gradingSchemeRows.value, gradingSchemeColumns))
''',
'''const filteredRows = computed(() => filterRows(applyStatusFilter(activeRows.value), activeColumns.value))
const filteredGradingSchemes = computed(() => filterRows(applyStatusFilter(gradingSchemeRows.value), gradingSchemeColumns))
''',
        "status-filtered rows",
    )

    text = replace_once(
        text,
'''  return `${filteredRows.value.length} of ${activeRows.value.length} records shown.`
''',
'''  const inactiveCount = activeRows.value.filter((row) => row.is_active === false).length
  return `${filteredRows.value.length} of ${activeRows.value.length} records shown · ${inactiveCount} inactive.`
''',
        "record summary inactive count",
    )

    text = insert_after(
        text,
'''function filterRows(rows, columns) {
''',
'''  rows = applyStatusFilter(rows)
''',
        "filterRows status guard",
    ) if "rows = applyStatusFilter(rows)" not in text else text

    # Avoid double filtering by removing the wrapper if we inserted guard? Keep both is harmless, but cleaner to use guard only once.
    text = text.replace(
'''const filteredRows = computed(() => filterRows(applyStatusFilter(activeRows.value), activeColumns.value))
const filteredGradingSchemes = computed(() => filterRows(applyStatusFilter(gradingSchemeRows.value), gradingSchemeColumns))
''',
'''const filteredRows = computed(() => filterRows(activeRows.value, activeColumns.value))
const filteredGradingSchemes = computed(() => filterRows(gradingSchemeRows.value, gradingSchemeColumns))
''')

    text = insert_after(
        text,
'''function activeOnly(list) {
  return list.filter((row) => row.is_active !== false)
}
''',
'''
function applyStatusFilter(rows) {
  if (recordStatusFilter.value === 'ACTIVE') return rows.filter((row) => row.is_active !== false)
  if (recordStatusFilter.value === 'INACTIVE') return rows.filter((row) => row.is_active === false)
  return rows
}
''',
        "applyStatusFilter helper",
    )

    # Ensure tab switch clears only search; keep status selection so admin can switch areas while viewing inactive.
    text = insert_after(
        text,
'''async function deactivate(url, id) {
  if (!window.confirm('Deactivate this record? Existing inspections will remain linked, but this item will no longer appear as active.')) return
  clearAlerts()
  try {
    await api.delete(`${url}/${id}`)
    await load()
    ok('Record deactivated successfully.')
  } catch (e) {
    fail(e)
  }
}
''',
'''
async function activate(url, id) {
  if (!window.confirm('Activate this record again? It will become selectable wherever active master data is used.')) return
  clearAlerts()
  try {
    await api.put(`${url}/${id}/activate`)
    await load()
    ok('Record activated successfully.')
  } catch (e) {
    fail(e)
  }
}
''',
        "activate function",
    )

    text = insert_after(
        text,
'''function deactivateCurrent(id) {
  const urls = {
    lines: '/master/lines',
    stations: '/master/stations',
    contractors: '/master/contractors',
    contracts: '/master/contracts',
    attributes: '/master/inspection-attributes',
    subareas: '/master/inspection-sub-areas'
  }
  deactivate(urls[activeTab.value], id)
}
''',
'''
function activateCurrent(id) {
  const urls = {
    lines: '/master/lines',
    stations: '/master/stations',
    contractors: '/master/contractors',
    contracts: '/master/contracts',
    attributes: '/master/inspection-attributes',
    subareas: '/master/inspection-sub-areas'
  }
  activate(urls[activeTab.value], id)
}
''',
        "activateCurrent function",
    )

    # Add a small visual style for activate buttons if a danger style exists.
    if ".activate-action {" not in text:
        text = text.replace(
'''.danger-action {
''',
'''.activate-action {
  color: #166534;
  border-color: #86efac;
  background: #f0fdf4;
}

.danger-action {
''')

    path.write_text(text, encoding="utf-8")


def patch_access_control_frontend() -> None:
    path = FRONTEND_ROOT / "src" / "views" / "AccessControlView.vue"
    text = path.read_text(encoding="utf-8")

    if "user-status-filter" not in text:
        text = replace_once(
            text,
'''        <input class="input" v-model.trim="userSearch" placeholder="Search name, username, emp no, role" />
''',
'''        <div class="user-filter-grid">
          <input class="input" v-model.trim="userSearch" placeholder="Search name, username, emp no, role" />
          <select class="input user-status-filter" v-model="userStatusFilter">
            <option value="ALL">All users</option>
            <option value="ACTIVE">Active only</option>
            <option value="INACTIVE">Inactive only</option>
          </select>
        </div>
''',
            "AccessControl user status filter template",
        )

    text = insert_after(
        text,
'''const userSearch = ref('')
''',
'''const userStatusFilter = ref('ALL')
''',
        "userStatusFilter ref",
    )

    old_filtered = '''const filteredUsers = computed(() => {
  const q = userSearch.value.toLowerCase()
  if (!q) return users.value
  return users.value.filter((u) => [u.name, u.username, u.emp_number, u.email, u.mobile, u.role]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(q)))
})
'''
    new_filtered = '''const filteredUsers = computed(() => {
  const q = userSearch.value.toLowerCase()
  let source = users.value
  if (userStatusFilter.value === 'ACTIVE') source = source.filter((u) => u.is_active)
  if (userStatusFilter.value === 'INACTIVE') source = source.filter((u) => !u.is_active)
  if (!q) return source
  return source.filter((u) => [u.name, u.username, u.emp_number, u.email, u.mobile, u.role]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(q)))
})
'''
    if old_filtered in text:
        text = replace_once(text, old_filtered, new_filtered, "AccessControl filteredUsers status filter")
    elif "userStatusFilter.value" not in text:
        raise SystemExit("Could not patch AccessControl filteredUsers.")

    if ".user-filter-grid" not in text:
        text = text.replace(
'''.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
''',
'''.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.user-filter-grid { display: grid; grid-template-columns: minmax(0, 1fr) 170px; gap: 10px; }
@media (max-width: 700px) { .user-filter-grid { grid-template-columns: 1fr; } }
''')

    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_master_backend()
    patch_master_frontend()
    patch_access_control_frontend()
    print("Master/access-control reactivation patch applied.")


if __name__ == "__main__":
    main()
