from pathlib import Path

DASHBOARD_VIEW = r"""<template>
  <AppLayout>
    <section class="card hero-panel dashboard-hero">
      <div class="toolbar hero-toolbar">
        <div>
          <h1>Operations Cleanliness Command Dashboard</h1>
          <p class="hero-subtitle">
            Analyse KPI-6 inspections, contractor performance, station trends and penalties with a clear month-wise or custom date scope.
          </p>
        </div>
        <div class="role-pill">{{ auth.user?.role }} view</div>
      </div>

      <div class="scope-panel section-gap">
        <div class="scope-header">
          <div>
            <p class="eyebrow">Analysis Scope</p>
            <h2>Choose one time scope, then narrow by contract or station</h2>
          </div>
          <div class="scope-summary">
            <span v-for="chip in scopeChips" :key="chip" class="scope-chip">{{ chip }}</span>
          </div>
        </div>

        <div class="filter-grid dashboard-filter-grid">
          <label>
            <span class="label">Time scope</span>
            <select class="input" v-model="filters.date_mode">
              <option value="billing">Billing month</option>
              <option value="custom">Custom date range</option>
            </select>
            <small class="field-help">Avoids mixing billing month with manual From/To dates.</small>
          </label>

          <label v-if="filters.date_mode === 'billing'">
            <span class="label">Billing month</span>
            <select class="input" v-model.number="filters.billing_cycle_id">
              <option :value="0">Select billing month</option>
              <option v-for="cycle in billingCycles" :key="cycle.id" :value="cycle.id">
                {{ cycleLabel(cycle) }}
              </option>
            </select>
            <small class="field-help">From/To dates are automatically taken from selected month.</small>
          </label>

          <template v-else>
            <label>
              <span class="label">From date</span>
              <input class="input" type="date" v-model="filters.from_date" :max="today" />
              <small class="field-help">Start date for inspection trend and report PDF.</small>
            </label>
            <label>
              <span class="label">To date</span>
              <input class="input" type="date" v-model="filters.to_date" :max="today" />
              <small class="field-help">End date for inspection trend and report PDF.</small>
            </label>
          </template>

          <label>
            <span class="label">Trend grouping</span>
            <select class="input" v-model="filters.period">
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="yearly">Yearly</option>
            </select>
            <small class="field-help">Controls only chart grouping, not the selected date scope.</small>
          </label>
        </div>

        <div class="filter-grid searchable-filter-grid section-gap-tight">
          <div class="combo-field" @keydown.escape="contractOpen = false">
            <span class="label">Contract</span>
            <div class="combo-input-wrap">
              <input
                class="input combo-input"
                type="search"
                v-model="contractSearch"
                placeholder="Search contract code or name"
                @focus="contractOpen = true"
                @input="contractOpen = true"
                @blur="closeCombosSoon"
              />
              <button v-if="filters.contract_id" class="combo-clear" type="button" @mousedown.prevent="clearContract">Clear</button>
            </div>
            <div v-if="contractOpen" class="combo-menu">
              <button class="combo-option" type="button" @mousedown.prevent="clearContract">
                <strong>All contracts</strong>
                <small>Show every contract in your scope</small>
              </button>
              <button
                v-for="contract in visibleContractOptions"
                :key="contract.id"
                class="combo-option"
                :class="{ selected: Number(filters.contract_id) === Number(contract.id) }"
                type="button"
                @mousedown.prevent="selectContract(contract)"
              >
                <strong>{{ contract.contract_code || `Contract ${contract.id}` }}</strong>
                <small>{{ contract.contract_name || 'No contract name' }}</small>
              </button>
              <div v-if="contractOverflowCount" class="combo-note">{{ contractOverflowCount }} more contract(s). Refine search to narrow the list.</div>
              <div v-if="!visibleContractOptions.length" class="combo-note">No contract matched your search.</div>
            </div>
            <small class="field-help">Searchable and scrollable for large contract lists.</small>
          </div>

          <div class="combo-field" @keydown.escape="stationOpen = false">
            <span class="label">Station</span>
            <div class="combo-input-wrap">
              <input
                class="input combo-input"
                type="search"
                v-model="stationSearch"
                placeholder="Search station name or code"
                @focus="stationOpen = true"
                @input="stationOpen = true"
                @blur="closeCombosSoon"
              />
              <button v-if="filters.station_id" class="combo-clear" type="button" @mousedown.prevent="clearStation">Clear</button>
            </div>
            <div v-if="stationOpen" class="combo-menu">
              <button class="combo-option" type="button" @mousedown.prevent="clearStation">
                <strong>All stations</strong>
                <small>{{ filters.contract_id ? 'All stations mapped to selected contract' : 'Show every station in your scope' }}</small>
              </button>
              <button
                v-for="station in visibleStationOptions"
                :key="station.id"
                class="combo-option"
                :class="{ selected: Number(filters.station_id) === Number(station.id) }"
                type="button"
                @mousedown.prevent="selectStation(station)"
              >
                <strong>{{ station.station_name || `Station ${station.id}` }}</strong>
                <small>{{ station.station_code || `Station ID ${station.id}` }}</small>
              </button>
              <div v-if="stationOverflowCount" class="combo-note">{{ stationOverflowCount }} more station(s). Refine search to narrow the list.</div>
              <div v-if="!visibleStationOptions.length" class="combo-note">No station matched your search.</div>
            </div>
            <small class="field-help">Station list is filtered by contract and stays scrollable as stations increase.</small>
          </div>

          <div class="filter-actions-card">
            <span class="label">Actions</span>
            <div class="filter-actions">
              <button class="btn btn-primary" type="button" @click="load" :disabled="loading">
                {{ loading ? 'Applying...' : 'Apply Scope' }}
              </button>
              <button class="btn btn-outline" type="button" @click="resetFilters" :disabled="loading">Reset</button>
            </div>
            <small class="field-help">The same scope is used for charts and dashboard PDF report.</small>
          </div>
        </div>
      </div>
    </section>

    <section v-if="error" class="card section-gap error-card">
      <p>{{ error }}</p>
    </section>

    <div class="stat-grid section-gap">
      <StatCard label="Contracts" :value="analytics.summary?.contracts ?? 0" :foot="selectedContractLabel" />
      <StatCard label="Stations" :value="analytics.summary?.stations ?? 0" :foot="selectedStationLabel" />
      <StatCard label="Inspections" :value="analytics.summary?.inspections ?? 0" :foot="activeDateLabel" />
      <StatCard label="Pending Reviews" :value="analytics.summary?.pending_reviews ?? 0" foot="Action required" />
      <StatCard label="Penalty Amount" :value="currency(analytics.summary?.penalty_amount || 0)" :foot="penaltyFootnote" />
    </div>

    <div class="grid grid-3 section-gap dashboard-grid">
      <div class="card span-2">
        <div class="card-title">
          <div>
            <h2>KPI-6 Score Trend</h2>
            <p class="muted small-text">Grouped {{ filters.period }} within {{ activeDateLabel }}.</p>
          </div>
          <span class="badge blue">{{ filters.period }}</span>
        </div>
        <SimpleLineChart :items="analytics.score_trend || []" />
      </div>
      <div class="card">
        <div class="card-title">
          <div>
            <h2>Latest Contract Score</h2>
            <p class="muted small-text">Score for selected scope.</p>
          </div>
          <span class="badge" :class="scoreClass(latestScore)">{{ latestScore }}%</span>
        </div>
        <DonutChart :value="latestScore" label="KPI-6">
          <p class="muted">Penalty threshold is configured contract-wise. Open KPI module for station-level gaps and generated penalties.</p>
          <RouterLink class="btn btn-secondary" to="/kpi">Open KPI module</RouterLink>
        </DonutChart>
      </div>
    </div>

    <div class="grid grid-2 section-gap">
      <div class="card">
        <div class="card-title">
          <div>
            <h2>Station-wise Score</h2>
            <p class="muted small-text">Lowest scoring stations appear first in the selected contract/date scope.</p>
          </div>
          <span class="badge">Score %</span>
        </div>
        <SimpleBarChart :items="analytics.station_scores || []" suffix="%" />
      </div>
      <div class="card">
        <div class="card-title">
          <div>
            <h2>Inspection Volume</h2>
            <p class="muted small-text">Inspection count by selected trend grouping.</p>
          </div>
          <span class="badge">Count</span>
        </div>
        <SimpleBarChart :items="analytics.inspection_volume || []" />
      </div>
    </div>

    <div class="grid grid-2 section-gap">
      <div class="card">
        <div class="card-title">
          <div>
            <h2>Grade Distribution</h2>
            <p class="muted small-text">Grade spread for inspections in the current scope.</p>
          </div>
          <span class="badge blue">A to F</span>
        </div>
        <SimpleBarChart :items="analytics.grade_distribution || []" />
      </div>
      <div class="card report-card">
        <div class="card-title">
          <div>
            <h2>Reports for Selected Scope</h2>
            <p class="muted small-text">Reports below use the same month/date, contract and station filters shown at the top.</p>
          </div>
          <span class="badge green">PDF</span>
        </div>

        <div class="report-scope-box">
          <span>Current report scope</span>
          <strong>{{ reportScopeLabel }}</strong>
          <small>{{ selectedContractLabel }} · {{ selectedStationLabel }}</small>
        </div>

        <div class="report-action-list">
          <article>
            <div>
              <strong>Inspection Register PDF</strong>
              <small>Downloads the filtered inspection register for the selected scope.</small>
            </div>
            <button class="btn btn-primary" type="button" @click="downloadRangePdf" :disabled="loading">Download</button>
          </article>
          <article>
            <div>
              <strong>Detailed Reports workspace</strong>
              <small>Use when you need more report-specific filters or individual inspection PDFs.</small>
            </div>
            <RouterLink class="btn btn-outline" to="/reports">Open Reports</RouterLink>
          </article>
          <article>
            <div>
              <strong>KPI & Penalty analysis</strong>
              <small>Open the KPI module for billing month, contract, station gap and penalty drill-down.</small>
            </div>
            <RouterLink class="btn btn-secondary" to="/kpi">Open KPI</RouterLink>
          </article>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import StatCard from '../components/StatCard.vue'
import SimpleBarChart from '../components/SimpleBarChart.vue'
import SimpleLineChart from '../components/SimpleLineChart.vue'
import DonutChart from '../components/DonutChart.vue'
import { api, downloadBlob } from '../services/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const analytics = ref({ summary: {} })
const master = ref({ contracts: [], stations: [], billing_cycles: [], contract_stations: [] })
const loading = ref(false)
const error = ref('')
const today = new Date().toISOString().split('T')[0]

const filters = reactive({
  date_mode: 'billing',
  billing_cycle_id: 0,
  period: 'monthly',
  from_date: firstDayOfCurrentMonth(),
  to_date: today,
  contract_id: '',
  station_id: ''
})

const contractSearch = ref('')
const stationSearch = ref('')
const contractOpen = ref(false)
const stationOpen = ref(false)

const billingCycles = computed(() => [...(master.value.billing_cycles || [])].sort((a, b) => String(b.start_date || '').localeCompare(String(a.start_date || ''))))
const contracts = computed(() => [...(master.value.contracts || [])].sort((a, b) => contractLabel(a).localeCompare(contractLabel(b))))
const stations = computed(() => [...(master.value.stations || [])].sort((a, b) => stationLabel(a).localeCompare(stationLabel(b))))
const contractById = computed(() => Object.fromEntries(contracts.value.map((row) => [Number(row.id), row])))
const stationById = computed(() => Object.fromEntries(stations.value.map((row) => [Number(row.id), row])))
const cycleById = computed(() => Object.fromEntries(billingCycles.value.map((row) => [Number(row.id), row])))
const selectedCycle = computed(() => cycleById.value[Number(filters.billing_cycle_id)] || null)
const selectedContract = computed(() => contractById.value[Number(filters.contract_id)] || null)
const selectedStation = computed(() => stationById.value[Number(filters.station_id)] || null)

const latestScore = computed(() => {
  const trend = analytics.value.score_trend || []
  const lastTrend = trend.length ? Number(trend[trend.length - 1].value || 0) : 0
  return Number(analytics.value.summary?.latest_score || lastTrend || 0)
})

const stationOptions = computed(() => {
  if (!filters.contract_id) return stations.value
  const mappedIds = new Set((master.value.contract_stations || [])
    .filter((row) => Number(row.contract_id) === Number(filters.contract_id))
    .map((row) => Number(row.station_id)))
  return stations.value.filter((station) => mappedIds.has(Number(station.id)))
})

const filteredContractOptions = computed(() => {
  const term = normalise(contractSearch.value)
  if (!term || selectedContract.value?.contract_code === contractSearch.value || contractLabel(selectedContract.value) === contractSearch.value) return contracts.value
  return contracts.value.filter((contract) => normalise(contractLabel(contract)).includes(term))
})
const filteredStationOptions = computed(() => {
  const term = normalise(stationSearch.value)
  if (!term || selectedStation.value?.station_name === stationSearch.value || stationLabel(selectedStation.value) === stationSearch.value) return stationOptions.value
  return stationOptions.value.filter((station) => normalise(stationLabel(station)).includes(term))
})
const visibleContractOptions = computed(() => filteredContractOptions.value.slice(0, 80))
const visibleStationOptions = computed(() => filteredStationOptions.value.slice(0, 100))
const contractOverflowCount = computed(() => Math.max(0, filteredContractOptions.value.length - visibleContractOptions.value.length))
const stationOverflowCount = computed(() => Math.max(0, filteredStationOptions.value.length - visibleStationOptions.value.length))

const selectedContractLabel = computed(() => selectedContract.value ? contractLabel(selectedContract.value) : 'All contracts')
const selectedStationLabel = computed(() => selectedStation.value ? stationLabel(selectedStation.value) : (filters.contract_id ? 'All mapped stations' : 'All stations'))
const activeDateLabel = computed(() => {
  if (filters.date_mode === 'billing') {
    return selectedCycle.value ? `${formatDate(selectedCycle.value.start_date)} to ${formatDate(selectedCycle.value.end_date)}` : 'Select billing month'
  }
  return `${formatDate(filters.from_date)} to ${formatDate(filters.to_date)}`
})
const reportScopeLabel = computed(() => filters.date_mode === 'billing' && selectedCycle.value ? cycleLabel(selectedCycle.value) : activeDateLabel.value)
const penaltyFootnote = computed(() => filters.date_mode === 'billing' ? 'Generated for selected billing month' : 'Generated penalties in selected scope')
const scopeChips = computed(() => [
  filters.date_mode === 'billing' ? 'Billing month' : 'Custom dates',
  activeDateLabel.value,
  selectedContractLabel.value,
  selectedStationLabel.value
])

function firstDayOfCurrentMonth() {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  return `${now.getFullYear()}-${month}-01`
}
function normalise(value) { return String(value || '').trim().toLowerCase() }
function scoreClass(v) { return v >= 90 ? 'green' : v >= 80 ? 'amber' : 'red' }
function currency(v) { return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v || 0) }
function formatDate(value) {
  if (!value) return '-'
  if (/^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
    const parts = String(value).split('-')
    return `${parts[2]}/${parts[1]}/${parts[0]}`
  }
  return new Date(value).toLocaleDateString('en-IN')
}
function cycleLabel(cycle) {
  if (!cycle) return '-'
  const name = cycle.name || cycle.code || `Cycle ${cycle.id}`
  return `${name} · ${formatDate(cycle.start_date)} to ${formatDate(cycle.end_date)}`
}
function contractLabel(contract) {
  if (!contract) return '-'
  const code = contract.contract_code || `Contract ${contract.id}`
  return contract.contract_name ? `${code} · ${contract.contract_name}` : code
}
function stationLabel(station) {
  if (!station) return '-'
  const name = station.station_name || `Station ${station.id}`
  return station.station_code ? `${name} · ${station.station_code}` : name
}
function closeCombosSoon() { window.setTimeout(() => { contractOpen.value = false; stationOpen.value = false }, 140) }
function selectContract(contract) {
  filters.contract_id = contract?.id || ''
  contractSearch.value = contract ? contractLabel(contract) : ''
  contractOpen.value = false
  if (filters.station_id && !stationOptions.value.some((station) => Number(station.id) === Number(filters.station_id))) clearStation()
}
function clearContract() { filters.contract_id = ''; contractSearch.value = ''; contractOpen.value = false }
function selectStation(station) { filters.station_id = station?.id || ''; stationSearch.value = station ? stationLabel(station) : ''; stationOpen.value = false }
function clearStation() { filters.station_id = ''; stationSearch.value = ''; stationOpen.value = false }
function syncComboLabels() {
  contractSearch.value = selectedContract.value ? contractLabel(selectedContract.value) : ''
  stationSearch.value = selectedStation.value ? stationLabel(selectedStation.value) : ''
}
function validateScope() {
  if (filters.date_mode === 'billing' && !filters.billing_cycle_id) return 'Select a billing month or switch to Custom date range.'
  if (filters.date_mode === 'custom') {
    if (!filters.from_date || !filters.to_date) return 'Select both From date and To date.'
    if (filters.from_date > filters.to_date) return 'From date cannot be after To date.'
  }
  return ''
}
function analyticsParams() {
  const params = { period: filters.period }
  if (filters.date_mode === 'billing' && selectedCycle.value) {
    params.billing_cycle_id = filters.billing_cycle_id
    params.from_date = selectedCycle.value.start_date
    params.to_date = selectedCycle.value.end_date
  } else {
    params.from_date = filters.from_date
    params.to_date = filters.to_date
  }
  if (filters.contract_id) params.contract_id = filters.contract_id
  if (filters.station_id) params.station_id = filters.station_id
  return params
}
function reportParams() {
  const params = { ...analyticsParams() }
  delete params.period
  delete params.billing_cycle_id
  return params
}
function reportFilename() {
  const period = (filters.date_mode === 'billing' && selectedCycle.value ? (selectedCycle.value.code || selectedCycle.value.name || 'billing-month') : `${filters.from_date}-to-${filters.to_date}`)
    .replace(/[^a-z0-9]+/gi, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase()
  const contract = selectedContract.value ? (selectedContract.value.contract_code || `contract-${selectedContract.value.id}`) : 'all-contracts'
  const station = selectedStation.value ? (selectedStation.value.station_code || selectedStation.value.station_name || `station-${selectedStation.value.id}`) : 'all-stations'
  return `${period}-${contract}-${station}-inspection-register.pdf`.replace(/[^a-z0-9.]+/gi, '-').toLowerCase()
}
async function load() {
  const validation = validateScope()
  if (validation) { error.value = validation; return }
  loading.value = true
  error.value = ''
  try {
    analytics.value = (await api.get('/dashboard/analytics', { params: analyticsParams() })).data
  } catch (e) {
    const detail = e?.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : 'Unable to load dashboard analytics for selected scope.'
  } finally {
    loading.value = false
  }
}
async function loadMaster() {
  master.value = (await api.get('/master/bootstrap')).data || { contracts: [], stations: [], billing_cycles: [], contract_stations: [] }
  if (!filters.billing_cycle_id && billingCycles.value.length) filters.billing_cycle_id = Number(billingCycles.value[0].id)
  syncComboLabels()
}
async function downloadRangePdf() {
  const validation = validateScope()
  if (validation) { error.value = validation; return }
  try {
    await downloadBlob('/reports/inspections/pdf', reportParams(), reportFilename())
  } catch (e) {
    const detail = e?.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : 'Unable to download inspection register PDF.'
  }
}
function resetFilters() {
  filters.date_mode = 'billing'
  filters.billing_cycle_id = billingCycles.value.length ? Number(billingCycles.value[0].id) : 0
  filters.period = 'monthly'
  filters.from_date = firstDayOfCurrentMonth()
  filters.to_date = today
  filters.contract_id = ''
  filters.station_id = ''
  contractSearch.value = ''
  stationSearch.value = ''
  error.value = ''
  load()
}

onMounted(async () => { await loadMaster(); await load() })
</script>

<style scoped>
.dashboard-hero { display: grid; gap: 4px; }
.hero-toolbar { align-items: flex-start; }
.scope-panel { border: 1px solid #dbeafe; border-radius: 24px; background: linear-gradient(135deg, #f8fbff 0%, #ffffff 100%); padding: 18px; box-shadow: 0 12px 30px rgba(15,23,42,.05); }
.scope-header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 14px; }
.scope-header h2 { margin: 0; color: #0f172a; font-size: 20px; }
.eyebrow { margin: 0 0 5px; color: #1d4ed8; font-weight: 1000; letter-spacing: .08em; text-transform: uppercase; font-size: 12px; }
.scope-summary { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; max-width: 52%; }
.scope-chip { display: inline-flex; border-radius: 999px; background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; padding: 7px 10px; font-weight: 900; font-size: 12px; }
.dashboard-filter-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); align-items: start; }
.searchable-filter-grid { grid-template-columns: minmax(260px, 1.4fr) minmax(260px, 1.4fr) minmax(220px, .8fr); align-items: start; }
.section-gap-tight { margin-top: 12px; }
.field-help { display: block; color: #64748b; font-size: 12px; line-height: 1.35; margin-top: 6px; font-weight: 700; }
.combo-field { position: relative; min-width: 0; }
.combo-input-wrap { position: relative; }
.combo-input { padding-right: 74px; }
.combo-clear { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); border: 0; background: #e2e8f0; color: #0f172a; border-radius: 999px; padding: 5px 9px; font-weight: 900; cursor: pointer; }
.combo-menu { position: absolute; z-index: 35; left: 0; right: 0; top: calc(100% - 16px); max-height: 286px; overflow-y: auto; border: 1px solid #bfdbfe; border-radius: 18px; background: #fff; box-shadow: 0 22px 60px rgba(15,23,42,.18); padding: 8px; }
.combo-option { width: 100%; border: 0; background: transparent; text-align: left; border-radius: 14px; padding: 10px 12px; cursor: pointer; display: grid; gap: 3px; }
.combo-option:hover, .combo-option.selected { background: #eff6ff; }
.combo-option strong { color: #0f172a; font-size: 14px; }
.combo-option small { color: #64748b; font-weight: 700; }
.combo-note { padding: 10px 12px; color: #64748b; font-weight: 800; font-size: 12px; }
.filter-actions-card { border: 1px solid #e2e8f0; border-radius: 18px; padding: 12px; background: #fff; }
.filter-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 7px; }
.small-text { font-size: 13px; }
.error-card { border-color: #fecaca; background: #fef2f2; color: #991b1b; font-weight: 800; }
.error-card p { margin: 0; }
.dashboard-grid { align-items: stretch; }
.report-card { background: linear-gradient(135deg, #ffffff, #f8fbff); }
.report-scope-box { border: 1px solid #bfdbfe; background: #eff6ff; border-radius: 18px; padding: 12px; display: grid; gap: 5px; color: #1e3a8a; }
.report-scope-box span { font-size: 12px; font-weight: 1000; text-transform: uppercase; letter-spacing: .05em; }
.report-scope-box strong { color: #0f172a; }
.report-scope-box small { color: #475569; font-weight: 800; }
.report-action-list { display: grid; gap: 10px; margin-top: 12px; }
.report-action-list article { display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center; border: 1px solid #e2e8f0; border-radius: 18px; padding: 12px; background: #fff; }
.report-action-list strong { color: #0f172a; display: block; }
.report-action-list small { color: #64748b; display: block; line-height: 1.4; margin-top: 3px; }
@media (max-width: 1100px) {
  .dashboard-filter-grid, .searchable-filter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .scope-summary { max-width: none; justify-content: flex-start; }
  .scope-header { display: grid; }
}
@media (max-width: 700px) {
  .dashboard-filter-grid, .searchable-filter-grid, .report-action-list article { grid-template-columns: 1fr; }
  .scope-panel { padding: 14px; border-radius: 20px; }
  .combo-menu { position: relative; top: 6px; max-height: 240px; }
}
</style>
"""


def find_project_root():
    current = Path.cwd().resolve()
    candidates = [current, current.parent]
    if current.name.lower() == "scripts":
        candidates.append(current.parent.parent)
    for base in candidates:
        if (base / "frontend" / "src" / "views").exists():
            return base
    raise RuntimeError("Could not find project root. Run this script from mch-inspection-platform root or backend/scripts.")


def main():
    root = find_project_root()
    target = root / "frontend" / "src" / "views" / "DashboardView.vue"
    if not target.exists():
        raise RuntimeError("DashboardView.vue not found at {}".format(target))
    backup = target.with_suffix(".vue.dashboard-filter-revamp.bak")
    if not backup.exists():
        backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    target.write_text(DASHBOARD_VIEW, encoding="utf-8")
    print("Dashboard filter/report revamp applied:")
    print("- {}".format(target))
    print("Backup saved at:")
    print("- {}".format(backup))
    print("Rebuild frontend with: docker compose up -d --build frontend")


if __name__ == "__main__":
    main()
