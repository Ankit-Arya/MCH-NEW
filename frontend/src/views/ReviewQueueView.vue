<template>
  <AppLayout>
    <section class="card hero-panel">
      <h1>Review Queue</h1>
      <p class="hero-subtitle">
        Pending inspections are loaded page by page. Use the approval tracker to see when the inspection was done, submitted, and approved at each level before taking action.
      </p>
    </section>

    <section class="card section-gap">
      <div class="card-title list-header">
        <div>
          <h2>Pending Reviews</h2>
          <p class="muted small-text" v-if="pagination.total">
            Showing {{ pagination.from_record }}–{{ pagination.to_record }} of {{ pagination.total }} pending records
          </p>
          <p class="muted small-text" v-else>No pending review records</p>
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

      <div class="table-wrap desktop-table review-table-wrap">
        <table class="table tracker-table">
          <thead>
            <tr>
              <th>No</th>
              <th>Date</th>
              <th>Station</th>
              <th>Inspector</th>
              <th>Score</th>
              <th>Status / Tracker</th>
              <th>PDF</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="i in rows" :key="i.id">
              <td><strong>{{ i.inspection_no }}</strong><br /><span class="muted small-text">{{ shortType(i.inspection_type) }}</span></td>
              <td>{{ formatDate(i.inspection_date) }}</td>
              <td>{{ i.station_name || i.station_id }}<br /><span class="muted small-text">{{ i.contract_code || '-' }}</span></td>
              <td>{{ i.submitted_by_name || '-' }}</td>
              <td><strong>{{ displayPercent(i.score) }}</strong></td>
              <td>
                <button class="status-tracker-button" type="button" @click="openTracker(i)">
                  <span class="badge" :class="statusClass(i.status)">{{ statusLabel(i.status) }}</span>
                  <span class="tracker-button-sub">{{ trackerButtonText(i) }}</span>
                </button>
              </td>
              <td>
                <div class="pdf-actions">
                  <button class="btn btn-sm btn-outline" @click="viewPdf(i)" :disabled="pdfLoading">View</button>
                  <button class="btn btn-sm btn-secondary" @click="downloadPdf(i)">Download</button>
                </div>
              </td>
              <td><button class="btn btn-primary" @click="recommend(i)" :disabled="actingId === i.id">{{ actionLabel(i) }}</button></td>
            </tr>
            <tr v-if="!rows.length"><td colspan="8" class="muted">No pending reviews.</td></tr>
          </tbody>
        </table>
      </div>

      <div class="mobile-list">
        <article class="mobile-record-card" v-for="i in rows" :key="i.id">
          <div class="mobile-record-top">
            <strong>{{ i.inspection_no }}</strong>
            <span class="badge" :class="statusClass(i.status)">{{ statusLabel(i.status) }}</span>
          </div>
          <div class="mobile-record-grid">
            <span>Date</span><b>{{ formatDate(i.inspection_date) }}</b>
            <span>Station</span><b>{{ i.station_name || i.station_id }}</b>
            <span>Contract</span><b>{{ i.contract_code || '-' }}</b>
            <span>Inspector</span><b>{{ i.submitted_by_name || '-' }}</b>
            <span>Type</span><b>{{ shortType(i.inspection_type) }}</b>
            <span>Score</span><b>{{ displayPercent(i.score) }}</b>
          </div>
          <div class="mobile-action-row">
            <button class="status-tracker-button mobile-status-button" type="button" @click="openTracker(i)">
              <span class="badge" :class="statusClass(i.status)">{{ statusLabel(i.status) }}</span>
              <span class="tracker-button-sub">{{ trackerButtonText(i) }}</span>
            </button>
            <button class="btn btn-outline" @click="viewPdf(i)" :disabled="pdfLoading">View PDF</button>
            <button class="btn btn-secondary" @click="downloadPdf(i)">Download PDF</button>
            <button class="btn btn-primary review-button" @click="recommend(i)" :disabled="actingId === i.id">
              {{ actionLabel(i) }}
            </button>
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


    <section v-if="selectedTrackerRow" class="tracker-modal-backdrop" @click.self="closeTracker">
      <div class="tracker-modal-card">
        <div class="tracker-modal-header">
          <div>
            <p class="muted small-text">Approval tracker</p>
            <h2>{{ selectedTrackerRow.inspection_no }}</h2>
            <p class="muted small-text">
              {{ selectedTrackerRow.station_name || '-' }} · {{ selectedTrackerRow.submitted_by_name || '-' }} · Score {{ displayPercent(selectedTrackerRow.score) }}
            </p>
          </div>
          <button class="btn btn-outline" type="button" @click="closeTracker">Close</button>
        </div>

        <div class="tracker-status-summary">
          <span class="label">Current status</span>
          <span class="badge" :class="statusClass(selectedTrackerRow.status)">{{ statusLabel(selectedTrackerRow.status) }}</span>
        </div>

        <div class="workflow-tracker modal-tracker">
          <div v-for="stage in trackerStages(selectedTrackerRow)" :key="stage.label" class="tracker-step" :class="stage.status">
            <span class="tracker-dot"></span>
            <div class="tracker-copy">
              <strong>{{ stage.label }}</strong>
              <small>{{ formatDateTime(stage.at) }}<template v-if="stage.by"> · {{ stage.by }}</template><template v-if="stage.action"> · {{ actionName(stage.action) }}</template></small>
            </div>
          </div>
          <p v-if="!trackerStages(selectedTrackerRow).length" class="muted small-text">Tracker unavailable for this inspection.</p>
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
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import PdfPreviewModal from '../components/PdfPreviewModal.vue'
import { api, downloadBlob, getPdfBlobUrl } from '../services/api'

const rows = ref([])
const loading = ref(false)
const actingId = ref(null)
const pdfLoading = ref(false)

const pdfPreview = reactive({ open: false, url: '', title: '', downloadName: 'inspection.pdf' })
const selectedTrackerRow = ref(null)
const pagination = reactive({ page: 1, size: 20, total: 0, pages: 1, has_next: false, has_prev: false, from_record: 0, to_record: 0 })


function openTracker(row) {
  selectedTrackerRow.value = row
}

function closeTracker() {
  selectedTrackerRow.value = null
}

function trackerStages(row) {
  return row?.workflow_tracker?.stages || []
}

function trackerButtonText(row) {
  const stages = trackerStages(row)
  const done = stages.filter((stage) => stage.status === 'done').length
  const current = stages.find((stage) => stage.status === 'current')
  if (current) return `${done}/${stages.length} done · ${current.label}`
  if (stages.length) return `${done}/${stages.length} done · View trail`
  return 'View trail'
}

function applyPagination(data) {
  rows.value = data.items || []
  pagination.page = data.page || 1
  pagination.size = data.size || pagination.size
  pagination.total = data.total || 0
  pagination.pages = data.pages || 1
  pagination.has_next = Boolean(data.has_next)
  pagination.has_prev = Boolean(data.has_prev || data.has_previous)
  pagination.from_record = data.from_record || ((pagination.page - 1) * pagination.size + 1)
  pagination.to_record = data.to_record || Math.min(pagination.page * pagination.size, pagination.total)
  if (!pagination.total) { pagination.from_record = 0; pagination.to_record = 0 }
}

async function enrichWithWorkflow(items) {
  const missingIds = (items || []).filter((item) => !item.workflow_tracker).map((item) => item.id).filter(Boolean)
  if (!missingIds.length) return items || []
  try {
    const { data } = await api.post('/reviews/workflow-trackers', { inspection_ids: missingIds })
    const byId = Object.fromEntries((data || []).map((tracker) => [tracker.inspection_id, tracker]))
    return items.map((item) => ({ ...item, workflow_tracker: item.workflow_tracker || byId[item.id] }))
  } catch {
    return items || []
  }
}

function statusClass(s) {
  const text = String(s || '')
  return text.includes('APPROVED') || text.includes('REVIEWED') ? 'green' : text.includes('RECOMMENDED') ? 'blue' : 'amber'
}
function shortType(type) { return String(type || '').replace('_INSPECTION', '').replaceAll('_', ' ') }
function formatDate(value) {
  if (!value) return '-'
  if (/^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
    const [year, month, day] = String(value).split('-')
    return `${day}/${month}/${year}`
  }
  return new Date(value).toLocaleDateString('en-IN')
}
function formatDateTime(value) {
  if (!value) return 'Pending'
  if (/^\d{4}-\d{2}-\d{2}$/.test(String(value))) return formatDate(value)
  return new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}
function displayPercent(value) {
  if (value === null || value === undefined || value === '') return '-'
  return `${Number(value).toFixed(2).replace(/\.00$/, '')}%`
}
function actionName(action) {
  const labels = { RECOMMEND_PENALTY: 'Recommended', APPROVE: 'Approved', REJECT: 'Rejected', RETURN_FOR_CLARIFICATION: 'Returned', SEND_TO_GM: 'Sent to GM', GM_REVIEW: 'Reviewed' }
  return labels[action] || String(action || '').replaceAll('_', ' ')
}
function actionLabel(item) {
  if (item.status === 'LINE_MANAGER_RECOMMENDED') return 'Approve as DGM'
  if (item.status === 'GM_REVIEW_REQUIRED') return 'Review as GM'
  return 'Recommend Penalty'
}

async function loadPage() {
  loading.value = true
  try {
    const { data } = await api.get('/reviews/pending', { params: { page: pagination.page, size: pagination.size } })
    data.items = await enrichWithWorkflow(data.items || [])
    applyPagination(data)
  } finally { loading.value = false }
}
async function changeSize() { pagination.page = 1; await loadPage() }
async function goFirst() { pagination.page = 1; await loadPage() }
async function goPrev() { if (pagination.has_prev) { pagination.page -= 1; await loadPage() } }
async function goNext() { if (pagination.has_next) { pagination.page += 1; await loadPage() } }
async function goLast() { pagination.page = pagination.pages; await loadPage() }

function cleanupPdfUrl() { if (pdfPreview.url) { window.URL.revokeObjectURL(pdfPreview.url); pdfPreview.url = '' } }
function closePdfPreview() { pdfPreview.open = false; cleanupPdfUrl() }
function statusLabel(status) {
  const labels = { UNDER_LINE_MANAGER_REVIEW: 'SUBMITTED TO LINE MANAGER', LINE_MANAGER_RECOMMENDED: 'APPROVED BY LINE MANAGER', DGM_APPROVED: 'APPROVED BY DGM', DGM_REJECTED: 'REJECTED BY DGM', GM_REVIEW_REQUIRED: 'SENT TO GM/OPS', GM_REVIEWED: 'REVIEWED BY GM/OPS', DRAFT: 'DRAFT' }
  return labels[status] || status
}
async function viewPdf(item) {
  pdfLoading.value = true
  pdfPreview.open = true
  pdfPreview.title = `Inspection ${item.inspection_no}`
  pdfPreview.downloadName = `${item.inspection_no}.pdf`
  cleanupPdfUrl()
  try { pdfPreview.url = await getPdfBlobUrl(`/reports/inspection/${item.id}/pdf`, {}) }
  finally { pdfLoading.value = false }
}
async function downloadPdf(item) { await downloadBlob(`/reports/inspection/${item.id}/pdf`, {}, `${item.inspection_no}.pdf`) }
async function recommend(i) {
  actingId.value = i.id
  try {
    let endpoint = '/reviews/' + i.id + '/line-manager'
    let payload = { action: 'RECOMMEND_PENALTY', comments: 'Reviewed and recommended from frontend.', recommended_penalty_amount: 0 }
    if (i.status === 'LINE_MANAGER_RECOMMENDED') {
      endpoint = '/reviews/' + i.id + '/dgm'
      payload = { action: 'APPROVE', comments: 'Approved by DGM.', final_penalty_amount: 0 }
    }
    if (i.status === 'GM_REVIEW_REQUIRED') {
      endpoint = '/reviews/' + i.id + '/gm'
      payload = { action: 'GM_REVIEW', comments: 'Reviewed by GM.' }
    }
    await api.post(endpoint, payload)
    await loadPage()
    if (rows.value.length === 0 && pagination.page > 1) { pagination.page -= 1; await loadPage() }
  } finally { actingId.value = null }
}

onMounted(loadPage)
onBeforeUnmount(cleanupPdfUrl)
</script>

<style scoped>
.list-header { align-items: flex-start; gap: 16px; }
.small-text { font-size: 0.9rem; margin-top: 4px; }
.page-size-control { display: flex; align-items: center; gap: 8px; flex-wrap: nowrap; }
.compact-input { min-width: 92px; }
.review-table-wrap { overflow-x: auto; }
.tracker-table { min-width: 960px; }
.workflow-tracker { display: grid; gap: 10px; }
.tracker-step { display: grid; grid-template-columns: 12px 1fr; gap: 8px; align-items: start; color: #64748b; }
.tracker-dot { width: 10px; height: 10px; border-radius: 999px; background: #cbd5e1; margin-top: 3px; box-shadow: 0 0 0 3px #f1f5f9; }
.tracker-step.done .tracker-dot { background: #16a34a; box-shadow: 0 0 0 3px #dcfce7; }
.tracker-step.current .tracker-dot { background: #d97706; box-shadow: 0 0 0 3px #fef3c7; }
.tracker-copy { display: grid; gap: 2px; line-height: 1.25; }
.tracker-copy strong { color: #0f172a; font-size: 12px; }
.tracker-copy small { color: #64748b; font-weight: 700; font-size: 11px; }
.status-tracker-button { display: inline-flex; flex-direction: column; align-items: flex-start; gap: 5px; border: 1px solid #dbe3f0; background: #fff; border-radius: 14px; padding: 8px 10px; cursor: pointer; min-width: 170px; text-align: left; box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05); }
.status-tracker-button:hover { border-color: #93c5fd; background: #f8fbff; }
.tracker-button-sub { color: #475569; font-size: 11px; font-weight: 800; line-height: 1.25; }
.tracker-modal-backdrop { position: fixed; inset: 0; z-index: 70; background: rgba(15, 23, 42, 0.42); display: grid; place-items: center; padding: 18px; }
.tracker-modal-card { width: min(720px, 100%); max-height: min(760px, 92vh); overflow: auto; background: white; border-radius: 24px; padding: 22px; box-shadow: 0 28px 80px rgba(15, 23, 42, 0.28); }
.tracker-modal-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding-bottom: 14px; border-bottom: 1px solid #e2e8f0; }
.tracker-modal-header h2 { margin: 2px 0 4px; }
.tracker-status-summary { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 14px; }
.modal-tracker .tracker-step { padding: 10px; border: 1px solid #e2e8f0; border-radius: 16px; background: #f8fafc; }
.pdf-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.pagination-bar { display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap; padding-top: 18px; }
.page-indicator { font-weight: 800; color: #17345c; padding: 0 8px; }
.mobile-list { display: none; }
.mobile-action-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px; }
.mobile-status-button { grid-column: 1 / -1; width: 100%; }
.review-button { grid-column: 1 / -1; }
@media (max-width: 760px) {
  .desktop-table { display: none; }
  .mobile-list { display: grid; gap: 14px; }
  .mobile-record-card { border: 1px solid rgba(148, 163, 184, 0.28); border-radius: 22px; padding: 16px; background: rgba(255,255,255,0.86); box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08); }
  .mobile-record-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 12px; }
  .mobile-record-grid { display: grid; grid-template-columns: 104px 1fr; gap: 8px 12px; font-size: 0.92rem; }
  .mobile-record-grid span { color: #64748b; font-weight: 700; }
  .mobile-record-grid b { color: #0f172a; word-break: break-word; }
  .pagination-bar { justify-content: center; }
  .pagination-bar .btn { flex: 1 1 42%; }
  .page-indicator { width: 100%; text-align: center; order: -1; margin-bottom: 8px; }
  .page-size-control { width: 100%; justify-content: space-between; }
  .compact-input { width: 120px; }
  .mobile-action-row { grid-template-columns: 1fr; }
  .tracker-modal-card { padding: 18px; }
  .tracker-modal-header { flex-direction: column; }
}
</style>
