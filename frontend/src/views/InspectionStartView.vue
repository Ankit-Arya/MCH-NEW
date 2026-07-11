<template>
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


/* MOBILE-FIRST START INSPECTION PATCH */
@media (max-width: 760px) {
  form.card.grid { gap: 14px; }
  .mini { padding: 12px; }
  .hint { line-height: 1.4; }
}
/* END MOBILE-FIRST START INSPECTION PATCH */
</style>
