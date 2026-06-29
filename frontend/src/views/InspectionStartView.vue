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

      <div>
        <label class="label">Station</label>
        <select class="input" v-model="form.station_id" required>
          <option value="">Select station</option>
          <option v-for="s in startOptions.stations" :key="s.id" :value="s.id" :disabled="!s.is_startable">
            {{ s.station_name }}{{ !s.is_startable ? ` - ${s.message}` : '' }}
          </option>
        </select>
        <p v-if="startOptions.message" class="hint warning">{{ startOptions.message }}</p>
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
const startOptions = ref({ stations: [], inspection_type: '', current_role: '', message: '', kpi_categories: [] })
const error = ref('')
const form = ref({
  station_id: '',
  kpi_category: 'KPI_6_CLEANLINESS',
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

const selectedStation = computed(() => {
  const stationId = Number(form.value.station_id)
  return startOptions.value.stations.find((s) => Number(s.id) === stationId) || null
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

const canStart = computed(() => Boolean(selectedStation.value?.is_startable))

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

  try {
    const payload = {
      station_id: Number(form.value.station_id),
      kpi_category: form.value.kpi_category,
      latitude: form.value.latitude,
      longitude: form.value.longitude,
      gps_accuracy: form.value.gps_accuracy,
      device_info: form.value.device_info,
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
.error { color: #dc2626; font-weight: 700; }
.hint { margin-top: 6px; font-size: 13px; }
.warning { color: #b45309; font-weight: 600; }
.input[readonly] { background: #f8fafc; color: #334155; }
button:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
