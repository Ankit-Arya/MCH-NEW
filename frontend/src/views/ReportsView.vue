<template>
  <AppLayout>
    <section class="card hero-panel">
      <h1>Inspection Reports & PDF Register</h1>
      <p class="hero-subtitle">
        Search inspections by date range, Station Manager/EIT, station, contract, inspection type and status.
        Use View PDF for quick analysis and Download PDF for record keeping.
      </p>

      <div class="filter-grid section-gap">
        <label><span class="label">From</span><input class="input" type="date" v-model="filters.from_date" /></label>
        <label><span class="label">To</span><input class="input" type="date" v-model="filters.to_date" /></label>
        <label>
          <span class="label">Contract</span>
          <select class="input" v-model="filters.contract_id">
            <option value="">All</option>
            <option v-for="c in master.contracts" :key="c.id" :value="c.id">{{ c.contract_code }}</option>
          </select>
        </label>
        <label>
          <span class="label">Station</span>
          <select class="input" v-model="filters.station_id">
            <option value="">All</option>
            <option v-for="s in master.stations" :key="s.id" :value="s.id">{{ s.station_name }}</option>
          </select>
        </label>
        <label>
          <span class="label">SM / EIT</span>
          <select class="input" v-model="filters.submitted_by">
            <option value="">All</option>
            <option v-for="u in master.users" :key="u.id" :value="u.id">{{ u.name }}</option>
          </select>
        </label>
        <label>
          <span class="label">Type</span>
          <select class="input" v-model="filters.inspection_type">
            <option value="">All</option>
            <option>SM_INSPECTION</option>
            <option>EIT_INSPECTION</option>
            <option>SPECIAL_INSPECTION</option>
          </select>
        </label>
      </div>

      <div class="toolbar section-gap">
        <button class="btn btn-primary" @click="search" :disabled="loading">{{ loading ? 'Searching...' : 'Search' }}</button>
        <button class="btn btn-secondary" @click="viewRegister" :disabled="pdfLoading">View Filtered PDF</button>
        <button class="btn btn-secondary" @click="downloadRegister">Download Filtered PDF</button>
        <button class="btn btn-outline" @click="reset">Reset</button>
      </div>
    </section>

    <section class="card section-gap">
      <div class="card-title list-header">
        <div>
          <h2>Inspection Register</h2>
          <p class="muted small-text" v-if="pagination.total">
            Showing {{ pagination.from_record }}–{{ pagination.to_record }} of {{ pagination.total }} records
          </p>
          <p class="muted small-text" v-else>No records found for selected filters</p>
        </div>
        <div class="page-size-control">
          <span class="label">Rows</span>
          <select class="input compact-input" v-model.number="pagination.size" @change="changeSize">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </div>
      </div>

      <div class="table-wrap desktop-table">
        <table class="table">
          <thead>
            <tr>
              <th>Inspection No</th>
              <th>Date</th>
              <th>Station</th>
              <th>Contract</th>
              <th>Inspector</th>
              <th>Type</th>
              <th>Status</th>
              <th>Score</th>
              <th>PDF</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.id">
              <td><strong>{{ r.inspection_no }}</strong></td>
              <td>{{ formatDate(r.inspection_date) }}</td>
              <td>{{ r.station_name || '-' }}</td>
              <td>{{ r.contract_code || '-' }}</td>
              <td>{{ r.submitted_by_name || '-' }}</td>
              <td><span class="badge">{{ shortType(r.inspection_type) }}</span></td>
              <td><span class="badge" :class="statusClass(r.status)">{{ statusLabel(r.status) }}</span></td>
              <td><strong>{{ r.score }}%</strong></td>
              <td>
                <div class="pdf-actions">
                  <button class="btn btn-sm btn-outline" @click="viewSingle(r)" :disabled="pdfLoading">View</button>
                  <button class="btn btn-sm btn-primary" @click="downloadSingle(r.id, r.inspection_no)">Download</button>
                </div>
              </td>
            </tr>
            <tr v-if="!rows.length"><td colspan="9" class="muted">No inspections found.</td></tr>
          </tbody>
        </table>
      </div>

      <div class="mobile-list">
        <article class="mobile-record-card" v-for="r in rows" :key="r.id">
          <div class="mobile-record-top">
            <strong>{{ r.inspection_no }}</strong>
            <span class="badge" :class="statusClass(r.status)">{{ statusLabel(r.status) }}</span>
          </div>
          <div class="mobile-record-grid">
            <span>Date</span><b>{{ formatDate(r.inspection_date) }}</b>
            <span>Station</span><b>{{ r.station_name || '-' }}</b>
            <span>Contract</span><b>{{ r.contract_code || '-' }}</b>
            <span>Inspector</span><b>{{ r.submitted_by_name || '-' }}</b>
            <span>Type</span><b>{{ shortType(r.inspection_type) }}</b>
            <span>Score</span><b>{{ r.score }}%</b>
          </div>
          <div class="mobile-action-row">
            <button class="btn btn-outline" @click="viewSingle(r)" :disabled="pdfLoading">View PDF</button>
            <button class="btn btn-primary" @click="downloadSingle(r.id, r.inspection_no)">Download</button>
          </div>
        </article>
      </div>

      <div class="pagination-bar" v-if="pagination.total > 0">
        <button class="btn btn-outline" @click="goFirst" :disabled="!pagination.has_prev || loading">First</button>
        <button class="btn btn-outline" @click="goPrev" :disabled="!pagination.has_prev || loading">Previous</button>
        <span class="page-indicator">Page {{ pagination.page }} of {{ pagination.pages }}</span>
        <button class="btn btn-outline" @click="goNext" :disabled="!pagination.has_next || loading">Next</button>
        <button class="btn btn-outline" @click="goLast" :disabled="!pagination.has_next || loading">Last</button>
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
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import PdfPreviewModal from '../components/PdfPreviewModal.vue'
import { api, downloadBlob, getPdfBlobUrl } from '../services/api'

const rows = ref([])
const loading = ref(false)
const pdfLoading = ref(false)
const master = ref({ contracts: [], stations: [], users: [] })

const pdfPreview = reactive({
  open: false,
  url: '',
  title: '',
  downloadName: 'inspection.pdf'
})

const defaultFilters = () => ({
  from_date: '2026-01-01',
  to_date: '2026-05-31',
  contract_id: '',
  station_id: '',
  submitted_by: '',
  inspection_type: ''
})

const filters = reactive(defaultFilters())
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0,
  pages: 1,
  has_next: false,
  has_prev: false,
  from_record: 0,
  to_record: 0
})

function params(includePagination = true) {
  const base = Object.fromEntries(Object.entries(filters).filter(([_, v]) => v !== '' && v !== null))
  if (includePagination) {
    base.page = pagination.page
    base.size = pagination.size
  }
  return base
}

function applyPagination(data) {
  rows.value = data.items || []
  pagination.page = data.page || 1
  pagination.size = data.size || pagination.size
  pagination.total = data.total || 0
  pagination.pages = data.pages || 1
  pagination.has_next = Boolean(data.has_next)
  pagination.has_prev = Boolean(data.has_prev)
  pagination.from_record = data.from_record || 0
  pagination.to_record = data.to_record || 0
}

function statusClass(s) {
  const text = String(s || '')
  return text.includes('APPROVED') || text.includes('CLOSED') || text.includes('REVIEWED')
    ? 'green'
    : text.includes('REVIEW') || text.includes('RECOMMENDED')
      ? 'amber'
      : 'blue'
}

function shortType(type) {
  return String(type || '').replace('_INSPECTION', '').replaceAll('_', ' ')
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('en-IN')
}

async function loadMaster() {
  master.value = (await api.get('/master/bootstrap')).data
}

async function loadPage() {
  loading.value = true
  try {
    const { data } = await api.get('/reports/inspections/search', { params: params(true) })
    applyPagination(data)
  } finally {
    loading.value = false
  }
}

async function search() {
  pagination.page = 1
  await loadPage()
}

async function changeSize() {
  pagination.page = 1
  await loadPage()
}

async function goFirst() { pagination.page = 1; await loadPage() }
async function goPrev() { if (pagination.has_prev) { pagination.page -= 1; await loadPage() } }
async function goNext() { if (pagination.has_next) { pagination.page += 1; await loadPage() } }
async function goLast() { pagination.page = pagination.pages; await loadPage() }

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

function statusLabel(status) {
  const labels = {
    UNDER_LINE_MANAGER_REVIEW: 'SUBMITTED TO LINE MANAGER',
    LINE_MANAGER_RECOMMENDED: 'APPROVED BY LINE MANAGER',
    DGM_APPROVED: 'APPROVED BY DGM',
    DRAFT: 'DRAFT'
  }
  return labels[status] || status
}

async function openPdf(url, paramsObj, title, filename) {
  pdfLoading.value = true
  pdfPreview.open = true
  pdfPreview.title = title
  pdfPreview.downloadName = filename
  cleanupPdfUrl()
  try {
    pdfPreview.url = await getPdfBlobUrl(url, paramsObj || {})
  } finally {
    pdfLoading.value = false
  }
}

async function viewSingle(row) {
  await openPdf(`/reports/inspection/${row.id}/pdf`, {}, `Inspection ${row.inspection_no}`, `${row.inspection_no}.pdf`)
}

async function downloadSingle(id, no) {
  await downloadBlob(`/reports/inspection/${id}/pdf`, {}, `${no}.pdf`)
}

async function viewRegister() {
  await openPdf('/reports/inspections/pdf', params(false), 'Filtered Inspection Register', 'inspection-register.pdf')
}

async function downloadRegister() {
  await downloadBlob('/reports/inspections/pdf', params(false), 'inspection-register.pdf')
}

async function reset() {
  Object.assign(filters, defaultFilters())
  pagination.page = 1
  await loadPage()
}

onMounted(async () => {
  await loadMaster()
  await loadPage()
})

onBeforeUnmount(cleanupPdfUrl)
</script>

<style scoped>
.list-header {
  align-items: flex-start;
  gap: 16px;
}

.small-text {
  font-size: 0.9rem;
  margin-top: 4px;
}

.page-size-control {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
}

.compact-input {
  min-width: 92px;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  padding-top: 18px;
}

.page-indicator {
  font-weight: 800;
  color: #17345c;
  padding: 0 8px;
}

.pdf-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.mobile-list {
  display: none;
}

.mobile-action-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 14px;
}

@media (max-width: 760px) {
  .desktop-table {
    display: none;
  }

  .mobile-list {
    display: grid;
    gap: 14px;
  }

  .mobile-record-card {
    border: 1px solid rgba(148, 163, 184, 0.28);
    border-radius: 22px;
    padding: 16px;
    background: rgba(255,255,255,0.86);
    box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
  }

  .mobile-record-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 12px;
  }

  .mobile-record-grid {
    display: grid;
    grid-template-columns: 96px 1fr;
    gap: 8px 12px;
    font-size: 0.92rem;
  }

  .mobile-record-grid span {
    color: #64748b;
    font-weight: 700;
  }

  .mobile-record-grid b {
    color: #0f172a;
    word-break: break-word;
  }

  .pagination-bar {
    justify-content: center;
  }

  .pagination-bar .btn {
    flex: 1 1 42%;
  }

  .page-indicator {
    width: 100%;
    text-align: center;
    order: -1;
    margin-bottom: 8px;
  }

  .page-size-control {
    width: 100%;
    justify-content: space-between;
  }

  .compact-input {
    width: 120px;
  }

  .mobile-action-row {
    grid-template-columns: 1fr;
  }
}
</style>
