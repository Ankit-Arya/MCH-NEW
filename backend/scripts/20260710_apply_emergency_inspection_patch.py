from pathlib import Path
import re
import sys

def project_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2]

ROOT = project_root()

def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")

def write(rel: str, text: str) -> None:
    path = ROOT / rel
    path.write_text(text, encoding="utf-8")
    print(f"patched {rel}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Patch marker not found: {label}")
    return text.replace(old, new, 1)

def regex_replace_once(text: str, pattern: str, repl: str, label: str, flags=0) -> str:
    new_text, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Patch regex marker not found: {label}")
    return new_text

def patch_schema() -> None:
    rel = "backend/app/schemas/inspection.py"
    text = read(rel)
    if "is_emergency: bool = False" not in text:
        text = replace_once(
            text,
            "    device_info: dict | None = None\n    remarks: str | None = None\n",
            "    device_info: dict | None = None\n"
            "    remarks: str | None = None\n"
            "    is_emergency: bool = False\n"
            "    emergency_reason: str | None = None\n",
            "InspectionStartIn emergency fields",
        )
    write(rel, text)

def patch_inspection_service() -> None:
    rel = "backend/app/services/inspection_service.py"
    text = read(rel)

    text = text.replace(
        "    require_station_access(db, user, inspection.station_id)\n",
        "    require_inspection_station_access_for_edit(db, user, inspection)\n",
    )

    if "EMERGENCY_INSPECTION_ROLES" not in text:
        text = replace_once(
            text,
            "START_ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN}\n",
            "START_ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN}\n"
            "EMERGENCY_INSPECTION_ROLES = {RoleCode.STATION_MANAGER, RoleCode.EIT_MEMBER}\n",
            "emergency roles",
        )

    helper_block = """
def _is_emergency_station_start_allowed(user: User) -> bool:
    return bool(user.role and user.role.code in EMERGENCY_INSPECTION_ROLES)


def is_emergency_inspection(inspection: Inspection) -> bool:
    device_info = inspection.device_info if isinstance(inspection.device_info, dict) else {}
    return bool(device_info.get("emergency_inspection"))


def require_inspection_station_access_for_edit(db: Session, user: User, inspection: Inspection) -> None:
    \"\"\"Allow normal station access or the original submitter's emergency inspection.

    This is intentionally narrower than normal station access: emergency access is only
    for the user who started that emergency inspection and only for field inspector roles.
    \"\"\"
    try:
        require_station_access(db, user, inspection.station_id)
        return
    except HTTPException as exc:
        if exc.status_code != 403:
            raise
        if (
            inspection.submitted_by == user.id
            and _is_emergency_station_start_allowed(user)
            and is_emergency_inspection(inspection)
            and inspection.status in [InspectionStatus.DRAFT, InspectionStatus.RETURNED_FOR_CLARIFICATION]
        ):
            return
        raise


"""
    if "def is_emergency_inspection(" not in text:
        text = replace_once(
            text,
            "\ndef _require_start_station_access",
            "\n" + helper_block + "def _require_start_station_access",
            "insert emergency edit helpers",
        )

    new_require = """def _require_start_station_access(db: Session, user: User, payload: InspectionStartIn) -> bool:
    \"\"\"Return True when the start is an emergency inspection.

    Normal start remains restricted to directly mapped stations.
    Emergency start is allowed only for SM/EIT users and must carry a reason.
    \"\"\"
    station_id = int(payload.station_id)
    requested_emergency = bool(payload.is_emergency)
    direct_station_ids = _explicit_user_station_ids(db, user)

    if _is_start_admin(user):
        return requested_emergency

    if station_id in direct_station_ids:
        return requested_emergency

    if requested_emergency and _is_emergency_station_start_allowed(user):
        reason = (payload.emergency_reason or payload.remarks or "").strip()
        if len(reason) < 5:
            raise HTTPException(
                status_code=400,
                detail="Emergency inspection reason is required when selecting a station not directly mapped to your user.",
            )
        return True

    raise HTTPException(
        status_code=403,
        detail="You can start normal inspections only for stations directly mapped to your user. Use Emergency Inspection with reason if you are officially asked to inspect another station.",
    )
"""
    text = regex_replace_once(
        text,
        r"def _require_start_station_access\(db: Session, user: User, station_id: int\) -> None:\n.*?(?=\n\ndef _contract_for_start_station)",
        new_require,
        "replace _require_start_station_access",
        flags=re.S,
    )

    if "emergency_started = _require_start_station_access(db, user, payload)" not in text:
        text = replace_once(
            text,
            "def create_inspection(db: Session, payload: InspectionStartIn, user: User) -> Inspection:\n    _require_start_station_access(db, user, payload.station_id)\n\n    contract = _contract_for_start_station(db, payload.station_id)\n",
            "def create_inspection(db: Session, payload: InspectionStartIn, user: User) -> Inspection:\n"
            "    emergency_started = _require_start_station_access(db, user, payload)\n\n"
            "    contract = _contract_for_start_station(db, payload.station_id)\n",
            "create_inspection access call",
        )

    if "device_info = dict(payload.device_info or {})" not in text:
        text = replace_once(
            text,
            "    now = datetime.utcnow()\n    inspection = Inspection(\n",
            "    now = datetime.utcnow()\n"
            "    device_info = dict(payload.device_info or {})\n"
            "    remarks = payload.remarks\n"
            "    workflow_action = \"START_EMERGENCY\" if emergency_started else \"START\"\n"
            "    workflow_remarks = \"Inspection started\"\n"
            "    if emergency_started:\n"
            "        reason = (payload.emergency_reason or payload.remarks or \"\").strip()\n"
            "        device_info.update({\n"
            "            \"emergency_inspection\": True,\n"
            "            \"emergency_reason\": reason,\n"
            "            \"emergency_started_by_user_id\": user.id,\n"
            "            \"normal_station_assignment_bypassed\": int(payload.station_id) not in _explicit_user_station_ids(db, user),\n"
            "        })\n"
            "        workflow_remarks = f\"Emergency inspection started. Reason: {reason or 'Not provided'}\"\n"
            "        if reason and not remarks:\n"
            "            remarks = f\"Emergency inspection: {reason}\"\n\n"
            "    inspection = Inspection(\n",
            "create_inspection emergency metadata",
        )

    text = text.replace("        device_info=payload.device_info,\n", "        device_info=device_info,\n")
    text = text.replace("        remarks=payload.remarks,\n", "        remarks=remarks,\n")

    old_history = '    db.add(InspectionWorkflowHistory(inspection_id=inspection.id, from_status=None, to_status=InspectionStatus.DRAFT.value, action_by=user.id, action="START", remarks="Inspection started"))\n    audit_log(db, actor=user, action="INSPECTION_STARTED", entity_type="Inspection", entity_id=inspection.id)\n'
    new_history = '    db.add(InspectionWorkflowHistory(inspection_id=inspection.id, from_status=None, to_status=InspectionStatus.DRAFT.value, action_by=user.id, action=workflow_action, remarks=workflow_remarks))\n    audit_log(db, actor=user, action="INSPECTION_STARTED_EMERGENCY" if emergency_started else "INSPECTION_STARTED", entity_type="Inspection", entity_id=inspection.id, new_value={"station_id": payload.station_id, "emergency": emergency_started})\n'
    if old_history in text:
        text = text.replace(old_history, new_history, 1)

    write(rel, text)

def patch_inspections_endpoint() -> None:
    rel = "backend/app/api/v1/endpoints/inspections.py"
    text = read(rel)

    if "require_inspection_station_access_for_edit" not in text.split("from app.services.media_service")[0]:
        text = replace_once(
            text,
            "    submit_entry_based_inspection,\n    submit_inspection,\n)",
            "    submit_entry_based_inspection,\n    submit_inspection,\n    require_inspection_station_access_for_edit,\n)",
            "import emergency edit helper",
        )

    if "EMERGENCY_INSPECTION_ROLES" not in text:
        text = replace_once(
            text,
            "START_ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN}\n",
            "START_ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN}\n"
            "EMERGENCY_INSPECTION_ROLES = {RoleCode.STATION_MANAGER, RoleCode.EIT_MEMBER}\n",
            "endpoint emergency roles",
        )

    text = text.replace(
        "    require_station_access(db, user, inspection.station_id)\n",
        "    require_inspection_station_access_for_edit(db, user, inspection)\n",
    )

    new_start_options = """@router.get("/start-options")
def start_options(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    \"\"\"Options for Start Inspection.

    Normal station list remains restricted to stations directly mapped to the user.
    Emergency station list is separately returned for SM/EIT users so the frontend can
    show it only after the Emergency Inspection checkbox is selected.
    \"\"\"

    kpi_categories = [
        {"code": KPI_6_CLEANLINESS, "label": "KPI-6 Level of Cleanliness"},
        {"code": KPI_CHEMICALS, "label": "KPI Chemicals & Consumables"},
    ]
    can_emergency_start = bool(user.role and user.role.code in EMERGENCY_INSPECTION_ROLES)

    all_station_query = db.query(Station).filter(Station.is_active.is_(True)).order_by(Station.station_name)

    normal_query = all_station_query
    message = None
    if not _is_start_admin(user):
        station_ids = _explicit_user_station_ids(db, user)
        if not station_ids:
            normal_stations = []
            message = "No stations are directly mapped to this user."
        else:
            normal_stations = [_station_contract_status(db, station) for station in normal_query.filter(Station.id.in_(station_ids)).all()]
    else:
        normal_stations = [_station_contract_status(db, station) for station in normal_query.all()]

    emergency_stations = []
    if can_emergency_start and not _is_start_admin(user):
        direct_station_ids = _explicit_user_station_ids(db, user)
        for station in all_station_query.all():
            row = _station_contract_status(db, station)
            row["is_directly_assigned"] = station.id in direct_station_ids
            emergency_stations.append(row)

    return {
        "current_role": user.role.code.value if user.role else None,
        "inspection_type": _inspection_type_for_user(user).value,
        "kpi_categories": kpi_categories,
        "stations": normal_stations,
        "emergency_stations": emergency_stations,
        "can_emergency_start": can_emergency_start,
        "message": message,
    }


"""
    text = regex_replace_once(
        text,
        r"@router\.get\(\"/start-options\"\)\ndef start_options\(.*?\n(?=\n@router\.get\(\"/checklist\"\))",
        new_start_options,
        "replace start_options",
        flags=re.S,
    )

    new_checklist = """@router.get("/checklist")
def checklist(contract_id: int, station_id: int, inspection_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        require_station_access(db, user, station_id)
    except HTTPException as exc:
        if exc.status_code != 403 or not inspection_id:
            raise
        inspection = db.get(Inspection, inspection_id)
        if not inspection or int(inspection.station_id) != int(station_id):
            raise
        require_inspection_station_access_for_edit(db, user, inspection)

    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    grading = db.query(GradingOption).filter_by(scheme_id=contract.grading_scheme_id).order_by(GradingOption.sort_order).all()
    attributes = db.query(InspectionAttribute).filter_by(is_active=True).order_by(InspectionAttribute.sort_order).all()
    sub_areas = db.query(InspectionSubArea).filter_by(is_active=True).order_by(InspectionSubArea.sort_order).all()
    return {
        "contract": contract,
        "station": db.get(Station, station_id),
        "grading_options": grading,
        "grades": grading,
        "attributes": attributes,
        "sub_areas": sub_areas,
    }


"""
    text = regex_replace_once(
        text,
        r"@router\.get\(\"/checklist\"\)\ndef checklist\(.*?\n(?=\n@router\.post\(\"/start\")",
        new_checklist,
        "replace checklist",
        flags=re.S,
    )

    write(rel, text)

def patch_kpi_chemicals() -> None:
    rel = "backend/app/api/v1/endpoints/kpi_chemicals.py"
    text = read(rel)

    if "require_inspection_station_access_for_edit" not in text:
        text = replace_once(
            text,
            "from app.services.audit_service import audit_log\n",
            "from app.services.audit_service import audit_log\n"
            "from app.services.inspection_service import require_inspection_station_access_for_edit\n",
            "kpi chemicals import emergency helper",
        )

    text = text.replace(
        "    require_station_access(db, user, inspection.station_id)\n",
        "    require_inspection_station_access_for_edit(db, user, inspection)\n",
    )

    old = "    requirements = list_station_requirements(inspection.station_id, include_inactive=False, db=db, user=user)\n"
    new = """    requirements = [
        _requirement_row(row)
        for row in db.query(StationChemicalRequirement)
        .join(KpiChemical, KpiChemical.id == StationChemicalRequirement.chemical_id)
        .filter(
            StationChemicalRequirement.station_id == inspection.station_id,
            StationChemicalRequirement.is_active.is_(True),
            KpiChemical.is_active.is_(True),
        )
        .order_by(KpiChemical.sort_order, KpiChemical.name)
        .all()
    ]
"""
    if old in text:
        text = text.replace(old, new, 1)

    write(rel, text)

START_VIEW = """<template>
  <AppLayout>
    <h1>Start Inspection</h1>

    <form class="card grid" @submit.prevent="start">
      <div>
        <label class="label">KPI</label>
        <select class="input" v-model="form.kpi_category" required>
          <option v-for="kpi in kpiOptions" :key="kpi.code" :value="kpi.code">{{ kpi.label }}</option>
        </select>
        <p class="hint">Select KPI first. KPI-6 keeps the existing cleanliness form. Chemicals opens quantity inspection.</p>
      </div>

      <label v-if="startOptions.can_emergency_start" class="emergency-toggle">
        <input type="checkbox" v-model="form.is_emergency" @change="onEmergencyToggle" />
        <span>
          <strong>Emergency Inspection</strong>
          <small>Use only when you are officially asked to inspect a station not assigned to you.</small>
        </span>
      </label>

      <div v-if="form.is_emergency" class="card mini emergency-note">
        <strong>Emergency station selection enabled</strong>
        <p>This list shows all active stations. Contract will auto-fill after station selection. Emergency reason is mandatory and will be recorded with the inspection.</p>
      </div>

      <div>
        <label class="label">Station</label>
        <select class="input" v-model="form.station_id" required>
          <option value="">{{ form.is_emergency ? 'Select emergency station' : 'Select assigned station' }}</option>
          <option v-for="s in activeStations" :key="s.id" :value="s.id" :disabled="!s.is_startable">
            {{ s.station_name }}{{ s.is_directly_assigned ? ' (assigned)' : '' }}{{ !s.is_startable ? ` - ${s.message}` : '' }}
          </option>
        </select>
        <p v-if="startOptions.message && !form.is_emergency" class="hint warning">{{ startOptions.message }}</p>
      </div>

      <div class="grid grid-2">
        <div>
          <label class="label">Mapped Contract</label>
          <input class="input" :value="mappedContractText" readonly />
          <p v-if="selectedStation?.message" class="hint warning">{{ selectedStation.message }}</p>
        </div>
        <div>
          <label class="label">Inspection Type</label>
          <input class="input" :value="inspectionTypeText" readonly />
        </div>
      </div>

      <label v-if="form.is_emergency">
        <span class="label">Emergency Reason</span>
        <textarea
          class="input"
          rows="3"
          v-model.trim="form.emergency_reason"
          required
          placeholder="Example: Directed by LM/Control due to leave/urgent requirement at this station"
        ></textarea>
      </label>

      <div class="card mini kpi-note" v-if="form.kpi_category === 'KPI_CHEMICALS'">
        <strong>Chemicals & Consumables KPI</strong>
        <p>The inspection will compare station-wise required quantity with actual available quantity and calculate shortfall.</p>
      </div>

      <div class="card mini">
        <strong>GPS</strong>
        <p>{{ gpsText }}</p>
        <button type="button" class="btn btn-muted" @click="captureGps">Capture GPS</button>
      </div>

      <textarea class="input" rows="3" v-model="form.remarks" placeholder="Initial remarks"></textarea>

      <button class="btn btn-primary" :disabled="!canStart">Start</button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'

const router = useRouter()
const startOptions = ref({
  stations: [],
  emergency_stations: [],
  inspection_type: '',
  current_role: '',
  message: '',
  kpi_categories: [],
  can_emergency_start: false
})
const error = ref('')
const form = ref({
  station_id: '',
  kpi_category: 'KPI_6_CLEANLINESS',
  is_emergency: false,
  emergency_reason: '',
  latitude: null,
  longitude: null,
  gps_accuracy: null,
  device_info: { userAgent: navigator.userAgent },
  remarks: ''
})

const fallbackKpiOptions = [
  { code: 'KPI_6_CLEANLINESS', label: 'KPI-6 Level of Cleanliness' },
  { code: 'KPI_CHEMICALS', label: 'KPI Chemicals & Consumables' }
]

const kpiOptions = computed(() => startOptions.value.kpi_categories?.length ? startOptions.value.kpi_categories : fallbackKpiOptions)
const activeStations = computed(() => form.value.is_emergency ? (startOptions.value.emergency_stations || []) : (startOptions.value.stations || []))

const selectedStation = computed(() => {
  const stationId = Number(form.value.station_id)
  return activeStations.value.find((s) => Number(s.id) === stationId) || null
})

const mappedContractText = computed(() => {
  if (!selectedStation.value) return 'Select station first'
  if (!selectedStation.value.contract_id) return 'No active contract mapped'
  return `${selectedStation.value.contract_code || ''} - ${selectedStation.value.contract_name || ''}`.trim()
})

const inspectionTypeText = computed(() => {
  const value = startOptions.value.inspection_type || '-'
  return value.replaceAll('_', ' ')
})

const gpsText = computed(() =>
  form.value.latitude
    ? `${form.value.latitude}, ${form.value.longitude} accuracy ${form.value.gps_accuracy || '-'}m`
    : 'Not captured'
)

const canStart = computed(() => {
  if (!selectedStation.value?.is_startable) return false
  if (form.value.is_emergency && !String(form.value.emergency_reason || '').trim()) return false
  return true
})

function onEmergencyToggle() {
  form.value.station_id = ''
  error.value = ''
}

function captureGps() {
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      form.value.latitude = pos.coords.latitude
      form.value.longitude = pos.coords.longitude
      form.value.gps_accuracy = pos.coords.accuracy
    },
    () => { error.value = 'GPS permission denied or unavailable' },
    { enableHighAccuracy: true, timeout: 10000 }
  )
}

onMounted(async () => {
  error.value = ''
  try {
    startOptions.value = (await api.get('/inspections/start-options')).data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Unable to load start inspection options'
  }
})

async function start() {
  error.value = ''
  if (!selectedStation.value?.is_startable) {
    error.value = selectedStation.value?.message || 'Please select a mapped station with one active contract'
    return
  }
  if (form.value.is_emergency && !String(form.value.emergency_reason || '').trim()) {
    error.value = 'Emergency reason is required'
    return
  }

  try {
    const payload = {
      station_id: Number(form.value.station_id),
      kpi_category: form.value.kpi_category,
      is_emergency: Boolean(form.value.is_emergency),
      emergency_reason: form.value.is_emergency ? form.value.emergency_reason : null,
      latitude: form.value.latitude,
      longitude: form.value.longitude,
      gps_accuracy: form.value.gps_accuracy,
      device_info: {
        ...form.value.device_info,
        emergency_inspection_requested: Boolean(form.value.is_emergency),
        selected_station_name: selectedStation.value?.station_name || null
      },
      remarks: form.value.remarks
    }
    const { data } = await api.post('/inspections/start', payload)
    router.push(`/inspections/${data.id}?contract_id=${data.contract_id}&station_id=${data.station_id}`)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Unable to start inspection'
  }
}
</script>

<style scoped>
.mini { background: #f8fafc; }
.kpi-note { border: 1px solid #bfdbfe; background: #eff6ff; color: #1e3a8a; }
.emergency-toggle { display: flex; align-items: flex-start; gap: 12px; padding: 14px; border: 1px solid #fed7aa; border-radius: 16px; background: #fff7ed; color: #7c2d12; cursor: pointer; }
.emergency-toggle input { margin-top: 4px; width: 18px; height: 18px; }
.emergency-toggle strong { display: block; }
.emergency-toggle small { display: block; margin-top: 3px; color: #9a3412; line-height: 1.35; }
.emergency-note { border: 1px solid #fed7aa; background: #fff7ed; color: #7c2d12; }
.error { color: #dc2626; font-weight: 700; }
.hint { margin-top: 6px; font-size: 13px; }
.warning { color: #b45309; font-weight: 600; }
.input[readonly] { background: #f8fafc; color: #334155; }
button:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
"""

def patch_frontend() -> None:
    write("frontend/src/views/InspectionStartView.vue", START_VIEW)

    rel = "frontend/src/views/InspectionFormView.vue"
    text = read(rel)
    old = "      const check = (await api.get(`/inspections/checklist?contract_id=${contractId}&station_id=${stationId}`)).data\n"
    new = "      const check = (await api.get('/inspections/checklist', { params: { contract_id: contractId, station_id: stationId, inspection_id: inspection.value.id } })).data\n"
    if old in text:
        text = text.replace(old, new, 1)
    write(rel, text)

def main() -> None:
    patch_schema()
    patch_inspection_service()
    patch_inspections_endpoint()
    patch_kpi_chemicals()
    patch_frontend()
    print("\\nEmergency inspection patch applied successfully.")
    print("Rebuild with: docker compose up -d --build api frontend")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Patch failed: {exc}", file=sys.stderr)
        sys.exit(1)
