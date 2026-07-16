<template>
  <AppLayout>
    <section class="card hero-panel action-hero">
      <div>
        <p class="eyebrow">Action Required</p>
        <h1>Drafts & Returned Inspections</h1>
        <p class="hero-subtitle">
          Continue saved draft inspections and correct inspections returned for clarification. These records are separated from completed reports so field action is not missed.
        </p>
      </div>
      <div class="hero-stats">
        <div class="stat-chip">
          <span>Total</span>
          <strong>{{ pagination.total }}</strong>
        </div>
        <div class="stat-chip amber-chip">
          <span>Draft</span>
          <strong>{{ counts.draft }}</strong>
        </div>
        <div class="stat-chip red-chip">
          <span>Returned</span>
          <strong>{{ counts.returned }}</strong>
        </div>
      </div>
    </section>

    <section class="card section-gap action-card">
      <div class="card-title action-title-row">
        <div>
          <h2>Items waiting for your action</h2>
          <p class="muted small-text" v-if="pagination.total">
            Showing {{ pagination.from_record }}–{{ pagination.to_record }} of {{ pagination.total }} record{{ pagination.total === 1 ? '' : 's' }}
          </p>
          <p class="muted small-text" v-else>No draft or returned inspections are pending for you.</p>
        </div>
        <button class="btn btn-outline" type="button" @click="loadPage" :disabled="loading">
          {{ loading ? 'Refreshing...' : 'Refresh' }}
        </button>
      </div>

      <div v-if="success" class="state-box success-box">
        <strong>Done</strong>
        <span>{{ success }}</span>
      </div>
      <div v-if="loading" class="state-box">Loading action-required inspections...</div>
      <div v-else-if="error" class="state-box error-box">
        <strong>Unable to load action-required records</strong>
        <span>{{ error }}</span>
      </div>
      <div v-else-if="!rows.length" class="empty-state">
        <h3>No action required</h3>
        <p>Drafts and returned inspections will appear here automatically.</p>
        <RouterLink class="btn btn-primary" to="/inspections/start">Start New Inspection</RouterLink>
      </div>

      <div v-else class="action-list">
        <article v-for="item in rows" :key="item.id" class="action-item" :class="statusCardClass(item.status)">
          <div class="action-main">
            <div class="action-head">
              <div>
                <strong>{{ item.inspection_no }}</strong>
                <p>{{ item.station_name || item.station_id }} · {{ item.contract_code || '-' }}</p>
              </div>
              <span class="badge" :class="statusBadgeClass(item.status)">{{ statusLabel(item.status) }}</span>
            </div>

            <div class="action-grid">
              <span>Inspection Date</span><b>{{ formatDate(item.inspection_date) }}</b>
              <span>Entries</span><b>{{ item.entry_count || 0 }}</b>
              <span>Evidence</span><b>{{ item.media_count || 0 }}</b>
              <span>Score</span><b>{{ displayPercent(item.score) }}</b>
            </div>

            <div class="reason-box">
              <strong>{{ item.reason }}</strong>
              <p v-if="item.latest_remarks">{{ item.latest_remarks }}</p>
              <small v-if="item.latest_actor || item.latest_action_at">
                <template v-if="item.latest_actor">By {{ item.latest_actor }}<template v-if="item.latest_actor_role"> ({{ roleLabel(item.latest_actor_role) }})</template></template>
                <template v-if="item.latest_action_at"> · {{ formatDateTime(item.latest_action_at) }}</template>
              </small>
            </div>
          </div>

          <div class="action-buttons">
            <RouterLink class="btn btn-primary" :to="`/inspections/${item.id}`">
              {{ item.status === 'RETURNED_FOR_CLARIFICATION' ? 'Correct & Resubmit' : 'Continue Draft' }}
            </RouterLink>
            <button class="btn btn-outline" type="button" @click="viewTrail(item)">View Trail</button>
            <button
              v-if="item.status === 'DRAFT' && item.can_delete_draft !== false"
              class="btn btn-outline danger-button"
              type="button"
              :disabled="deletingId === item.id"
              @click="deleteDraft(item)"
            >
              {{ deletingId === item.id ? 'Deleting...' : 'Delete Draft' }}
            </button>
          </div>
        </article>
      </div>

      <div class="pagination-bar" v-if="pagination.total > 0">
        <button class="btn btn-outline" @click="goPrev" :disabled="!pagination.has_prev || loading">Previous</button>
        <span class="page-indicator">Page {{ pagination.page }} of {{ pagination.pages }}</span>
        <button class="btn btn-outline" @click="goNext" :disabled="!pagination.has_next || loading">Next</button>
      </div>
    </section>

    <section v-if="selectedItem" class="trail-modal-backdrop" @click.self="selectedItem = null">
      <div class="trail-modal-card">
        <div class="trail-modal-header">
          <div>
            <p class="muted small-text">Action trail</p>
            <h2>{{ selectedItem.inspection_no }}</h2>
          </div>
          <button class="btn btn-outline" type="button" @click="selectedItem = null">Close</button>
        </div>
        <div class="trail-details">
          <span>Status</span><b>{{ statusLabel(selectedItem.status) }}</b>
          <span>Reason</span><b>{{ selectedItem.reason }}</b>
          <span>Latest action by</span><b>{{ selectedItem.latest_actor || '-' }}</b>
          <span>Role</span><b>{{ roleLabel(selectedItem.latest_actor_role) }}</b>
          <span>When</span><b>{{ formatDateTime(selectedItem.latest_action_at) }}</b>
          <span>Remarks</span><b>{{ selectedItem.latest_remarks || '-' }}</b>
        </div>
      </div>
    </section>
  </AppLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'

const rows = ref([])
const loading = ref(false)
const error = ref('')
const success = ref('')
const selectedItem = ref(null)
const deletingId = ref(null)
const counts = reactive({ draft: 0, returned: 0 })
const pagination = reactive({ page: 1, size: 20, total: 0, pages: 1, has_next: false, has_prev: false, from_record: 0, to_record: 0 })

function apiErrorText(e, fallback = 'Request failed') {
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
  if (detail) return JSON.stringify(detail)
  return e?.message || fallback
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
  counts.draft = Number(data.counts?.draft || 0)
  counts.returned = Number(data.counts?.returned || 0)
}

async function loadPage() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/inspections/action-required', { params: { page: pagination.page, size: pagination.size } })
    applyPagination(data)
  } catch (e) {
    error.value = apiErrorText(e, 'Unable to load action-required inspections')
  } finally {
    loading.value = false
  }
}

async function goPrev() { if (pagination.has_prev) { pagination.page -= 1; await loadPage() } }
async function goNext() { if (pagination.has_next) { pagination.page += 1; await loadPage() } }
function viewTrail(item) { selectedItem.value = item }

async function deleteDraft(item) {
  if (!item || item.status !== 'DRAFT') return
  const ok = window.confirm(
    `Delete draft inspection ${item.inspection_no}?\n\nThis will permanently remove the draft, its entries and uploaded evidence references. Submitted or returned inspections cannot be deleted.`
  )
  if (!ok) return

  deletingId.value = item.id
  error.value = ''
  success.value = ''
  try {
    await api.delete(`/inspections/${item.id}/draft`)
    success.value = `Draft inspection ${item.inspection_no} deleted successfully.`
    if (rows.value.length === 1 && pagination.page > 1) pagination.page -= 1
    await loadPage()
  } catch (e) {
    error.value = apiErrorText(e, 'Unable to delete draft inspection')
  } finally {
    deletingId.value = null
  }
}

function formatDate(value) {
  if (!value) return '-'
  if (/^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
    const [year, month, day] = String(value).split('-')
    return `${day}/${month}/${year}`
  }
  return new Date(value).toLocaleDateString('en-IN')
}
function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}
function displayPercent(value) {
  if (value === null || value === undefined || value === '') return '-'
  return `${Number(value).toFixed(2).replace(/\.00$/, '')}%`
}
function statusLabel(status) {
  const labels = {
    DRAFT: 'DRAFT - INCOMPLETE',
    RETURNED_FOR_CLARIFICATION: 'RETURNED FOR CLARIFICATION',
  }
  return labels[status] || String(status || '-').replaceAll('_', ' ')
}
function roleLabel(role) {
  const labels = {
    SUPER_ADMIN: 'Super Admin',
    HK_CELL_ADMIN: 'HK Cell Admin',
    GM_OPS: 'GM/Ops',
    DGM_LINE: 'DGM Line',
    DGM_HK: 'DGM HK',
    AM_MGR_LINE: 'Line Manager',
    AM_MGR_HK: 'HK Manager',
    STATION_MANAGER: 'Station Manager',
    EIT_MEMBER: 'External Inspection Team',
    AUDITOR: 'Auditor',
  }
  return labels[role] || role || '-'
}
function statusBadgeClass(status) { return status === 'RETURNED_FOR_CLARIFICATION' ? 'red' : 'amber' }
function statusCardClass(status) { return status === 'RETURNED_FOR_CLARIFICATION' ? 'returned-card' : 'draft-card' }

onMounted(loadPage)
</script>

<style scoped>
.action-hero { display: flex; justify-content: space-between; align-items: flex-start; gap: 18px; }
.eyebrow { margin: 0 0 5px; color: #991b1b; font-weight: 1000; letter-spacing: .08em; text-transform: uppercase; font-size: 12px; }
.hero-stats { display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
.stat-chip { min-width: 94px; border: 1px solid #dbeafe; border-radius: 18px; background: #fff; padding: 12px; display: grid; gap: 4px; text-align: center; box-shadow: 0 10px 24px rgba(15,23,42,.06); }
.stat-chip span { color: #64748b; font-size: 12px; font-weight: 900; }
.stat-chip strong { color: #0f172a; font-size: 24px; }
.amber-chip { border-color: #fde68a; background: #fffbeb; }
.red-chip { border-color: #fecaca; background: #fff1f2; }
.action-title-row { align-items: flex-start; gap: 14px; }
.small-text { font-size: .9rem; margin-top: 4px; }
.state-box, .empty-state { border: 1px dashed #cbd5e1; border-radius: 20px; padding: 22px; background: #f8fafc; color: #475569; }
.error-box { display: grid; gap: 6px; color: #991b1b; background: #fff1f2; border-color: #fecaca; }
.success-box { display: grid; gap: 6px; color: #166534; background: #f0fdf4; border-color: #bbf7d0; }
.empty-state { display: grid; gap: 10px; justify-items: start; }
.empty-state h3, .empty-state p { margin: 0; }
.action-list { display: grid; gap: 14px; }
.action-item { display: grid; grid-template-columns: 1fr auto; gap: 16px; border: 1px solid #dbeafe; border-radius: 24px; padding: 16px; background: #fff; box-shadow: 0 14px 34px rgba(15,23,42,.06); }
.action-item.returned-card { border-color: #fecaca; background: linear-gradient(135deg, #fff 0%, #fff7f7 100%); }
.action-item.draft-card { border-color: #fde68a; background: linear-gradient(135deg, #fff 0%, #fffbeb 100%); }
.action-main { display: grid; gap: 12px; }
.action-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.action-head strong { color: #0f172a; font-size: 18px; }
.action-head p { margin: 4px 0 0; color: #64748b; font-weight: 700; }
.action-grid { display: grid; grid-template-columns: repeat(4, minmax(110px, 1fr)); gap: 8px 12px; }
.action-grid span { color: #64748b; font-size: 12px; font-weight: 900; }
.action-grid b { color: #0f172a; }
.reason-box { border: 1px solid #e2e8f0; border-radius: 18px; background: rgba(255,255,255,.74); padding: 12px; display: grid; gap: 5px; }
.reason-box strong { color: #0f172a; }
.reason-box p { margin: 0; color: #334155; line-height: 1.5; }
.reason-box small { color: #64748b; font-weight: 800; }
.action-buttons { display: flex; flex-direction: column; gap: 10px; justify-content: center; min-width: 178px; }
.badge.red { background: #fee2e2; color: #991b1b; }
.danger-button { border-color: #fecaca; color: #991b1b; background: #fff7f7; }
.danger-button:hover:not(:disabled) { background: #fee2e2; }
.pagination-bar { display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap; padding-top: 18px; }
.page-indicator { font-weight: 900; color: #17345c; padding: 0 8px; }
.trail-modal-backdrop { position: fixed; inset: 0; z-index: 90; background: rgba(15,23,42,.42); display: grid; place-items: center; padding: 18px; }
.trail-modal-card { width: min(680px, 100%); max-height: 92vh; overflow: auto; background: white; border-radius: 24px; padding: 22px; box-shadow: 0 28px 80px rgba(15,23,42,.28); }
.trail-modal-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding-bottom: 14px; border-bottom: 1px solid #e2e8f0; }
.trail-details { display: grid; grid-template-columns: 150px 1fr; gap: 10px 14px; padding-top: 16px; }
.trail-details span { color: #64748b; font-weight: 900; }
.trail-details b { color: #0f172a; font-weight: 800; white-space: pre-wrap; }
@media (max-width: 860px) {
  .action-hero, .action-item { grid-template-columns: 1fr; display: grid; }
  .hero-stats { justify-content: stretch; }
  .stat-chip { flex: 1 1 30%; }
  .action-grid, .trail-details { grid-template-columns: 1fr; }
  .action-buttons { min-width: 0; }
}
</style>
