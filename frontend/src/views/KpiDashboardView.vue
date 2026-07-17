<template>
  <AppLayout>
    <section class="card hero-panel">
      <div class="toolbar">
        <div>
          <h1>KPI-6 & Penalty Intelligence</h1>
          <p class="hero-subtitle">
            Review monthly KPI-6 performance by billing month, contract and station. The page now shows names, periods,
            station gaps, penalty exposure and evidence reports instead of asking users to remember internal IDs.
          </p>
        </div>
        <button class="btn btn-secondary" @click="load" :disabled="loading">
          {{ loading ? 'Refreshing...' : 'Refresh' }}
        </button>
      </div>

      <div class="filter-grid section-gap kpi-filter-grid">
        <label>
          <span class="label">Billing month</span>
          <select class="input" v-model.number="selectedCycleId">
            <option :value="0">All months</option>
            <option v-for="cycle in billingCycles" :key="cycle.id" :value="cycle.id">
              {{ cycleLabel(cycle) }}
            </option>
          </select>
        </label>

        <label>
          <span class="label">Contract</span>
          <select class="input" v-model.number="selectedContractId">
            <option :value="0">All contracts</option>
            <option v-for="contract in contracts" :key="contract.id" :value="contract.id">
              {{ contractLabel(contract) }}
            </option>
          </select>
        </label>

        <label>
          <span class="label">Station</span>
          <select class="input" v-model.number="selectedStationId">
            <option :value="0">All stations</option>
            <option v-for="station in stationOptions" :key="station.id" :value="station.id">
              {{ station.station_name }}
            </option>
          </select>
        </label>

        <label>
          <span class="label">Show</span>
          <select class="input" v-model="riskFilter">
            <option value="all">All KPI rows</option>
            <option value="penalty">Penalty applicable</option>
            <option value="safe">No penalty</option>
            <option value="missing">Missing SM/EIT coverage</option>
          </select>
        </label>
      </div>

      <div class="action-row section-gap">
        <button class="btn btn-primary" @click="calculate" :disabled="calculating || !selectedCycleId || !selectedContractId">
          {{ calculating ? 'Checking GM approvals...' : 'Calculate after GM approval' }}
        </button>
        <button class="btn btn-secondary" @click="viewEvidenceRegister" :disabled="pdfLoading || !selectedCycleId">
          View monthly evidence report
        </button>
        <button class="btn btn-secondary" @click="downloadEvidenceRegister" :disabled="pdfLoading || !selectedCycleId">
          Download monthly evidence report
        </button>
        <RouterLink class="btn btn-outline" to="/reports">Open full reports</RouterLink>
      </div>

      <div class="plain-help section-gap">
        <strong>How to use:</strong>
        Select the billing month and contract name, calculate KPI-6 after GM/Ops final approval, then check the station drill-down.
        Only GM/Ops-approved inspections contribute to monthly KPI score and penalty; pending inspections block calculation.
      </div>
    </section>

    <section class="card section-gap error-card" v-if="error">
      <p>{{ error }}</p>
    </section>
    <section class="card section-gap success-card" v-if="success">
      <p>{{ success }}</p>
    </section>

    <section class="summary-grid section-gap">
      <StatCard label="Selected period" :value="selectedCycle ? cycleShortLabel(selectedCycle) : 'All months'" :foot="selectedCycleDateRange" />
      <StatCard label="Contracts reviewed" :value="summary.contracts" foot="Filtered KPI rows" />
      <StatCard label="Average score" :value="`${summary.averageScore}%`" foot="Across visible contracts" />
      <StatCard label="Penalty cases" :value="summary.penaltyCases" :foot="currency(summary.totalPenalty)" />
      <StatCard label="Attention stations" :value="summary.attentionStations" foot="Low score or missing inspection" />
    </section>

    <section class="grid grid-3 section-gap" v-if="result">
      <div class="card result-card span-2">
        <div class="card-title">
          <div>
            <h2>Latest calculation result</h2>
            <p class="muted small-text">{{ selectedContract ? contractLabel(selectedContract) : `Contract ${result.contract_id}` }}</p>
          </div>
          <span class="badge" :class="result.is_penalty_applicable ? 'red' : 'green'">
            {{ result.is_penalty_applicable ? 'Penalty applicable' : 'No penalty' }}
          </span>
        </div>
        <div class="calculation-grid">
          <div>
            <span>Average KPI-6 score</span>
            <strong>{{ percent(result.average_score) }}</strong>
          </div>
          <div>
            <span>Penalty amount</span>
            <strong>{{ currency(result.penalty_amount) }}</strong>
          </div>
          <div>
            <span>Billing month</span>
            <strong>{{ selectedCycle ? cycleShortLabel(selectedCycle) : result.billing_cycle_id }}</strong>
          </div>
        </div>
      </div>
      <div class="card guidance-card">
        <h2>Decision logic</h2>
        <p>
          KPI-6 compares the contract average against the configured contract threshold after GM/Ops final approval.
          Penalty amount is calculated from monthly bill value and contract penalty percentage only for approved monthly inspection data.
        </p>
      </div>
    </section>

    <section class="grid grid-2 section-gap">
      <div class="card">
        <div class="card-title">
          <div>
            <h2>Contract performance</h2>
            <p class="muted small-text">Lowest scores appear first so problem contracts are visible.</p>
          </div>
          <span class="badge blue">KPI-6</span>
        </div>
        <SimpleBarChart :items="scoreChart" suffix="%" />
      </div>

      <div class="card">
        <div class="card-title">
          <div>
            <h2>What needs attention</h2>
            <p class="muted small-text">Low-scoring stations and stations missing SM/EIT coverage.</p>
          </div>
          <span class="badge amber">Exceptions</span>
        </div>

        <div class="exception-list" v-if="attentionRows.length">
          <article v-for="row in attentionRows" :key="`attention-${row.id}`" class="exception-card">
            <div>
              <strong>{{ stationLabel(row.station_id) }}</strong>
              <span>{{ contractName(row.contract_id) }} · {{ cycleShortLabelById(row.billing_cycle_id) }}</span>
            </div>
            <div class="exception-score">
              <b>{{ percent(row.final_station_score) }}</b>
              <small>{{ stationIssue(row) }}</small>
            </div>
          </article>
        </div>
        <p v-else class="empty-note">No attention items for the selected filters.</p>
      </div>
    </section>

    <section class="card section-gap">
      <div class="card-title">
        <div>
          <h2>Contract KPI register</h2>
          <p class="muted small-text">
            Contract names, billing period and threshold are shown directly. Use report buttons to open the supporting inspection evidence.
          </p>
        </div>
        <span class="badge">{{ filteredScores.length }} rows</span>
      </div>

      <div class="table-wrap mobile-cards">
        <table class="table kpi-table">
          <thead>
            <tr>
              <th>Billing month</th>
              <th>Contract</th>
              <th>Stations</th>
              <th>Average</th>
              <th>Threshold</th>
              <th>Result</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredScores" :key="`score-${row.id}`">
              <td data-label="Billing month">{{ cycleShortLabelById(row.billing_cycle_id) }}</td>
              <td data-label="Contract">
                <strong>{{ contractName(row.contract_id) }}</strong><br />
                <span class="muted small-text">{{ contractCode(row.contract_id) }}</span>
              </td>
              <td data-label="Stations">{{ row.station_count || 0 }}</td>
              <td data-label="Average"><strong>{{ percent(row.average_score) }}</strong></td>
              <td data-label="Threshold">{{ percent(thresholdForContract(row.contract_id)) }}</td>
              <td data-label="Result">
                <span class="badge" :class="row.is_penalty_applicable ? 'red' : 'green'">
                  {{ row.is_penalty_applicable ? 'Penalty' : 'OK' }}
                </span>
                <span v-if="missingCoverageCount(row.billing_cycle_id, row.contract_id)" class="badge amber stack-badge">
                  {{ missingCoverageCount(row.billing_cycle_id, row.contract_id) }} station gap
                </span>
              </td>
              <td data-label="Evidence">
                <div class="table-actions">
                  <button class="btn btn-sm btn-outline" @click="viewEvidenceFor(row)" :disabled="pdfLoading">View</button>
                  <button class="btn btn-sm btn-secondary" @click="downloadEvidenceFor(row)" :disabled="pdfLoading">Download</button>
                </div>
              </td>
            </tr>
            <tr v-if="!filteredScores.length">
              <td colspan="7" class="muted">No KPI rows found for selected filters. Calculate KPI-6 for a billing month and contract.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="grid grid-2 section-gap">
      <div class="card">
        <div class="card-title">
          <div>
            <h2>Penalty register</h2>
            <p class="muted small-text">Readable penalty view with contract, bill value, score and amount.</p>
          </div>
          <span class="badge red">Penalty</span>
        </div>

        <div class="table-wrap mobile-cards">
          <table class="table penalty-table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Contract</th>
                <th>Score</th>
                <th>Monthly bill</th>
                <th>Penalty</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in filteredPenalties" :key="`penalty-${p.id}`">
                <td data-label="Period">{{ cycleShortLabelById(p.billing_cycle_id) }}</td>
                <td data-label="Contract">
                  <strong>{{ contractName(p.contract_id) }}</strong><br />
                  <span class="muted small-text">{{ contractCode(p.contract_id) }}</span>
                </td>
                <td data-label="Score">{{ percent(p.kpi_score) }}</td>
                <td data-label="Monthly bill">{{ currency(p.monthly_bill_value) }}</td>
                <td data-label="Penalty"><strong>{{ currency(p.penalty_amount) }}</strong></td>
                <td data-label="Status"><span class="badge amber">{{ p.status || 'GENERATED' }}</span></td>
              </tr>
              <tr v-if="!filteredPenalties.length">
                <td colspan="6" class="muted">No penalty rows found for selected filters.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-title">
          <div>
            <h2>Station score drill-down</h2>
            <p class="muted small-text">Shows whether SM and EIT inspections both contributed to the final station score.</p>
          </div>
          <span class="badge blue">Station level</span>
        </div>

        <div class="table-wrap mobile-cards station-table-wrap">
          <table class="table station-table">
            <thead>
              <tr>
                <th>Station</th>
                <th>Contract</th>
                <th>SM</th>
                <th>EIT</th>
                <th>Final</th>
                <th>Insight</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filteredStationRows" :key="`station-${row.id}`">
                <td data-label="Station"><strong>{{ stationLabel(row.station_id) }}</strong></td>
                <td data-label="Contract">{{ contractCode(row.contract_id) }}</td>
                <td data-label="SM">{{ row.sm_inspection_count || 0 }} · {{ percent(row.sm_average_score) }}</td>
                <td data-label="EIT">{{ row.eit_inspection_count || 0 }} · {{ percent(row.eit_average_score) }}</td>
                <td data-label="Final"><strong>{{ percent(row.final_station_score) }}</strong></td>
                <td data-label="Insight">
                  <span class="badge" :class="stationBadgeClass(row)">{{ stationIssue(row) }}</span>
                </td>
              </tr>
              <tr v-if="!filteredStationRows.length">
                <td colspan="6" class="muted">No station score rows found. Run monthly KPI calculation first.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <PdfPreviewModal
      :open="pdfPreview.open"
      :src="pdfPreview.url"
      :title="pdfPreview.title"
      :download-name="pdfPreview.downloadName"
      :loading="pdfLoading"
      @close="closePdfPreview"
    />
  </AppLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import PdfPreviewModal from '../components/PdfPreviewModal.vue'
import SimpleBarChart from '../components/SimpleBarChart.vue'
import StatCard from '../components/StatCard.vue'
import { api, downloadBlob, getPdfBlobUrl } from '../services/api'

const loading = ref(false)
const calculating = ref(false)
const pdfLoading = ref(false)
const error = ref('')
const success = ref('')
const result = ref(null)

const master = ref({ billing_cycles: [], contracts: [], stations: [], contract_stations: [] })
const scores = ref([])
const penalties = ref([])
const stationScores = ref([])

const selectedCycleId = ref(0)
const selectedContractId = ref(0)
const selectedStationId = ref(0)
const riskFilter = ref('all')

const pdfPreview = reactive({
  open: false,
  url: '',
  title: '',
  downloadName: 'kpi-evidence-register.pdf'
})

const billingCycles = computed(() => [...(master.value.billing_cycles || [])].sort((a, b) => String(b.start_date || '').localeCompare(String(a.start_date || ''))))
const contracts = computed(() => [...(master.value.contracts || [])].sort((a, b) => contractLabel(a).localeCompare(contractLabel(b))))
const stations = computed(() => [...(master.value.stations || [])].sort((a, b) => String(a.station_name || '').localeCompare(String(b.station_name || ''))))

const cycleById = computed(() => Object.fromEntries(billingCycles.value.map((row) => [Number(row.id), row])))
const contractById = computed(() => Object.fromEntries(contracts.value.map((row) => [Number(row.id), row])))
const stationById = computed(() => Object.fromEntries(stations.value.map((row) => [Number(row.id), row])))

const selectedCycle = computed(() => cycleById.value[Number(selectedCycleId.value)] || null)
const selectedContract = computed(() => contractById.value[Number(selectedContractId.value)] || null)

const selectedCycleDateRange = computed(() => selectedCycle.value ? `${formatDate(selectedCycle.value.start_date)} to ${formatDate(selectedCycle.value.end_date)}` : 'Use month filter for reports')

const stationOptions = computed(() => {
  if (!selectedContractId.value) return stations.value
  const mappedIds = new Set((master.value.contract_stations || [])
    .filter((row) => Number(row.contract_id) === Number(selectedContractId.value))
    .map((row) => Number(row.station_id)))
  return stations.value.filter((station) => mappedIds.has(Number(station.id)))
})

const filteredScores = computed(() => {
  return scores.value
    .filter((row) => matchesBaseFilters(row))
    .filter((row) => {
      if (riskFilter.value === 'penalty') return Boolean(row.is_penalty_applicable)
      if (riskFilter.value === 'safe') return !row.is_penalty_applicable
      if (riskFilter.value === 'missing') return missingCoverageCount(row.billing_cycle_id, row.contract_id) > 0
      return true
    })
    .sort((a, b) => Number(a.average_score || 0) - Number(b.average_score || 0))
})

const filteredPenalties = computed(() => {
  return penalties.value
    .filter((row) => matchesBaseFilters(row))
    .filter((row) => {
      if (riskFilter.value === 'penalty') return Number(row.penalty_amount || 0) > 0
      if (riskFilter.value === 'safe') return Number(row.penalty_amount || 0) <= 0
      if (riskFilter.value === 'missing') return missingCoverageCount(row.billing_cycle_id, row.contract_id) > 0
      return true
    })
    .sort((a, b) => Number(b.penalty_amount || 0) - Number(a.penalty_amount || 0))
})

const filteredStationRows = computed(() => {
  return stationScores.value
    .filter((row) => matchesBaseFilters(row))
    .filter((row) => !selectedStationId.value || Number(row.station_id) === Number(selectedStationId.value))
    .filter((row) => {
      if (riskFilter.value === 'penalty') return Number(row.final_station_score || 0) < thresholdForContract(row.contract_id)
      if (riskFilter.value === 'safe') return Number(row.final_station_score || 0) >= thresholdForContract(row.contract_id) && !hasMissingInspection(row)
      if (riskFilter.value === 'missing') return hasMissingInspection(row)
      return true
    })
    .sort((a, b) => Number(a.final_station_score || 0) - Number(b.final_station_score || 0))
})

const attentionRows = computed(() => filteredStationRows.value
  .filter((row) => hasMissingInspection(row) || Number(row.final_station_score || 0) < thresholdForContract(row.contract_id))
  .slice(0, 8))

const scoreChart = computed(() => filteredScores.value
  .slice(0, 10)
  .map((row) => ({ label: contractCode(row.contract_id), value: Number(row.average_score || 0) })))

const summary = computed(() => {
  const scoreRows = filteredScores.value
  const penaltyRows = filteredPenalties.value.filter((row) => Number(row.penalty_amount || 0) > 0)
  const averageScore = scoreRows.length
    ? scoreRows.reduce((sum, row) => sum + Number(row.average_score || 0), 0) / scoreRows.length
    : 0
  return {
    contracts: scoreRows.length,
    averageScore: round(averageScore),
    penaltyCases: penaltyRows.length,
    totalPenalty: penaltyRows.reduce((sum, row) => sum + Number(row.penalty_amount || 0), 0),
    attentionStations: filteredStationRows.value.filter((row) => hasMissingInspection(row) || Number(row.final_station_score || 0) < thresholdForContract(row.contract_id)).length
  }
})

function matchesBaseFilters(row) {
  if (selectedCycleId.value && Number(row.billing_cycle_id) !== Number(selectedCycleId.value)) return false
  if (selectedContractId.value && Number(row.contract_id) !== Number(selectedContractId.value)) return false
  return true
}

function clearMessages() {
  error.value = ''
  success.value = ''
}

function contractLabel(contract) {
  if (!contract) return '-'
  const code = contract.contract_code || `Contract ${contract.id}`
  return contract.contract_name ? `${code} · ${contract.contract_name}` : code
}

function contractCode(contractId) {
  const contract = contractById.value[Number(contractId)]
  return contract?.contract_code || `Contract ${contractId}`
}

function contractName(contractId) {
  const contract = contractById.value[Number(contractId)]
  return contract?.contract_name || contractCode(contractId)
}

function stationLabel(stationId) {
  const station = stationById.value[Number(stationId)]
  return station?.station_name || `Station ${stationId}`
}

function cycleLabel(cycle) {
  if (!cycle) return '-'
  return `${cycle.name || cycle.code || `Cycle ${cycle.id}`} · ${formatDate(cycle.start_date)} to ${formatDate(cycle.end_date)}`
}

function cycleShortLabel(cycle) {
  if (!cycle) return '-'
  return cycle.name || cycle.code || `Cycle ${cycle.id}`
}

function cycleShortLabelById(cycleId) {
  return cycleShortLabel(cycleById.value[Number(cycleId)]) || `Cycle ${cycleId}`
}

function thresholdForContract(contractId) {
  const contract = contractById.value[Number(contractId)]
  return Number(contract?.kpi6_threshold_percent ?? 90)
}

function hasMissingInspection(row) {
  return Number(row.sm_inspection_count || 0) === 0 || Number(row.eit_inspection_count || 0) === 0
}

function missingCoverageCount(cycleId, contractId) {
  return stationScores.value.filter((row) => Number(row.billing_cycle_id) === Number(cycleId)
    && Number(row.contract_id) === Number(contractId)
    && hasMissingInspection(row)).length
}

function stationIssue(row) {
  const issues = []
  if (Number(row.sm_inspection_count || 0) === 0) issues.push('No SM')
  if (Number(row.eit_inspection_count || 0) === 0) issues.push('No EIT')
  if (Number(row.final_station_score || 0) < thresholdForContract(row.contract_id)) issues.push('Below threshold')
  return issues.length ? issues.join(' · ') : 'Healthy'
}

function stationBadgeClass(row) {
  if (hasMissingInspection(row)) return 'amber'
  if (Number(row.final_station_score || 0) < thresholdForContract(row.contract_id)) return 'red'
  return 'green'
}

function reportParamsFor(row = {}) {
  const cycle = cycleById.value[Number(row.billing_cycle_id || selectedCycleId.value)]
  const params = {}
  if (cycle?.start_date) params.from_date = cycle.start_date
  if (cycle?.end_date) params.to_date = cycle.end_date
  const contractId = row.contract_id || selectedContractId.value
  if (contractId) params.contract_id = contractId
  if (selectedStationId.value) params.station_id = selectedStationId.value
  return params
}

function reportTitle(row = {}) {
  const period = cycleShortLabelById(row.billing_cycle_id || selectedCycleId.value)
  const contract = row.contract_id ? contractCode(row.contract_id) : selectedContract.value ? contractCode(selectedContract.value.id) : 'All contracts'
  return `${period} KPI-6 Evidence · ${contract}`
}

function reportFileName(row = {}) {
  const period = cycleShortLabelById(row.billing_cycle_id || selectedCycleId.value).replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '') || 'kpi6'
  const contract = row.contract_id ? contractCode(row.contract_id) : selectedContract.value ? contractCode(selectedContract.value.id) : 'all-contracts'
  return `${period}-${contract}-inspection-evidence.pdf`.toLowerCase()
}

function cleanupPdfUrl() {
  if (pdfPreview.url) {
    window.URL.revokeObjectURL(pdfPreview.url)
    pdfPreview.url = ''
  }
}

function closePdfPreview() {
  pdfPreview.open = false
  cleanupPdfUrl()
}

async function openPdf(url, params, title, filename) {
  pdfLoading.value = true
  pdfPreview.open = true
  pdfPreview.title = title
  pdfPreview.downloadName = filename
  cleanupPdfUrl()
  try {
    pdfPreview.url = await getPdfBlobUrl(url, params)
  } catch (e) {
    error.value = readableError(e, 'Unable to open evidence report')
    pdfPreview.open = false
  } finally {
    pdfLoading.value = false
  }
}

async function viewEvidenceRegister() {
  clearMessages()
  if (!selectedCycleId.value) {
    error.value = 'Select a billing month before opening the monthly evidence report.'
    return
  }
  await openPdf('/reports/inspections/pdf', reportParamsFor(), reportTitle(), reportFileName())
}

async function downloadEvidenceRegister() {
  clearMessages()
  if (!selectedCycleId.value) {
    error.value = 'Select a billing month before downloading the monthly evidence report.'
    return
  }
  try {
    await downloadBlob('/reports/inspections/pdf', reportParamsFor(), reportFileName())
  } catch (e) {
    error.value = readableError(e, 'Unable to download evidence report')
  }
}

async function viewEvidenceFor(row) {
  clearMessages()
  await openPdf('/reports/inspections/pdf', reportParamsFor(row), reportTitle(row), reportFileName(row))
}

async function downloadEvidenceFor(row) {
  clearMessages()
  try {
    await downloadBlob('/reports/inspections/pdf', reportParamsFor(row), reportFileName(row))
  } catch (e) {
    error.value = readableError(e, 'Unable to download evidence report')
  }
}

async function load() {
  loading.value = true
  clearMessages()
  try {
    const [{ data: bootstrap }, { data: contractScores }, { data: penaltyRows }, { data: stationRows }] = await Promise.all([
      api.get('/master/bootstrap'),
      api.get('/kpi/contract-scores'),
      api.get('/kpi/penalties'),
      api.get('/kpi/station-scores')
    ])
    master.value = bootstrap || { billing_cycles: [], contracts: [], stations: [], contract_stations: [] }
    scores.value = contractScores || []
    penalties.value = penaltyRows || []
    stationScores.value = stationRows || []

    if (!selectedCycleId.value && billingCycles.value.length) selectedCycleId.value = Number(billingCycles.value[0].id)
  } catch (e) {
    error.value = readableError(e, 'Unable to load KPI and penalty data')
  } finally {
    loading.value = false
  }
}

async function calculate() {
  clearMessages()
  if (!selectedCycleId.value || !selectedContractId.value) {
    error.value = 'Select both billing month and contract before calculating KPI-6.'
    return
  }
  calculating.value = true
  try {
    const { data } = await api.post('/kpi/calculate/monthly', {
      billing_cycle_id: Number(selectedCycleId.value),
      contract_id: Number(selectedContractId.value)
    })
    result.value = data
    success.value = `KPI-6 calculated for ${contractCode(selectedContractId.value)} in ${cycleShortLabelById(selectedCycleId.value)}.`
    await load()
  } catch (e) {
    error.value = readableError(e, 'Unable to calculate monthly KPI-6')
  } finally {
    calculating.value = false
  }
}

function readableError(e, fallback) {
  const detail = e?.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail.map((item) => `${(item.loc || []).slice(1).join('.') || 'Field'}: ${item.msg}`).join(' | ')
  }
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') return detail.message || JSON.stringify(detail)
  return fallback
}

function currency(value) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value || 0))
}

function percent(value) {
  return `${round(value)}%`
}

function round(value) {
  return Number(Number(value || 0).toFixed(2))
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('en-IN')
}

onMounted(load)
onBeforeUnmount(cleanupPdfUrl)
</script>

<style scoped>
.kpi-filter-grid {
  grid-template-columns: 1.2fr 1.6fr 1.2fr 1fr;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.plain-help {
  border: 1px solid #bfdbfe;
  background: #f8fbff;
  border-radius: 16px;
  color: #1e3a8a;
  padding: 12px 14px;
  line-height: 1.55;
}

.error-card {
  border-color: #fecaca;
  background: #fef2f2;
  color: #991b1b;
  font-weight: 800;
}

.error-card p,
.success-card p {
  margin: 0;
}

.success-card {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #166534;
  font-weight: 800;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
}

.small-text {
  font-size: 13px;
}

.result-card,
.guidance-card {
  background: linear-gradient(135deg, #ffffff, #f8fbff);
}

.calculation-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.calculation-grid div {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: white;
  padding: 14px;
}

.calculation-grid span {
  display: block;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 8px;
}

.calculation-grid strong {
  display: block;
  font-size: 24px;
  color: #0f172a;
}

.guidance-card p {
  color: #475569;
  line-height: 1.6;
  margin-bottom: 0;
}

.exception-list {
  display: grid;
  gap: 10px;
}

.exception-card {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #ffffff;
  padding: 12px;
}

.exception-card div:first-child {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
}

.exception-card span,
.exception-score small {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.exception-score {
  flex: 0 0 auto;
  text-align: right;
}

.exception-score b {
  display: block;
  color: #991b1b;
  font-size: 18px;
}

.empty-note {
  margin: 0;
  color: #64748b;
  padding: 18px;
  border: 1px dashed #dbe4ef;
  border-radius: 16px;
  background: #f8fafc;
}

.kpi-table {
  min-width: 980px;
}

.penalty-table {
  min-width: 860px;
}

.station-table {
  min-width: 820px;
}

.table-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stack-badge {
  margin-top: 6px;
}

@media (max-width: 1180px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .kpi-filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .summary-grid,
  .calculation-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .kpi-filter-grid {
    grid-template-columns: 1fr;
  }

  .action-row .btn,
  .action-row a.btn {
    width: 100%;
  }

  .exception-card {
    flex-direction: column;
  }

  .exception-score {
    text-align: left;
  }
}
</style>
