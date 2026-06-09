<template>
  <AppLayout>
    <section class="card hero-panel">
      <h1>Review Queue</h1>
      <p class="hero-subtitle">
        Pending inspections are loaded page by page so the queue remains fast even when inspections grow over time.
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

      <div class="table-wrap desktop-table">
        <table class="table">
          <thead>
            <tr>
              <th>No</th>
              <th>Date</th>
              <th>Station</th>
              <th>Contract</th>
              <th>Inspector</th>
              <th>Type</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="i in rows" :key="i.id">
              <td><strong>{{ i.inspection_no }}</strong></td>
              <td>{{ formatDate(i.inspection_date) }}</td>
              <td>{{ i.station_name || i.station_id }}</td>
              <td>{{ i.contract_code || '-' }}</td>
              <td>{{ i.submitted_by_name || '-' }}</td>
              <td><span class="badge">{{ shortType(i.inspection_type) }}</span></td>
              <td><span class="badge" :class="statusClass(i.status)">{{ i.status }}</span></td>
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
            <span class="badge" :class="statusClass(i.status)">{{ i.status }}</span>
          </div>
          <div class="mobile-record-grid">
            <span>Date</span><b>{{ formatDate(i.inspection_date) }}</b>
            <span>Station</span><b>{{ i.station_name || i.station_id }}</b>
            <span>Contract</span><b>{{ i.contract_code || '-' }}</b>
            <span>Inspector</span><b>{{ i.submitted_by_name || '-' }}</b>
            <span>Type</span><b>{{ shortType(i.inspection_type) }}</b>
          </div>
          <button class="btn btn-primary full-width" @click="recommend(i)" :disabled="actingId === i.id">
            {{ actionLabel(i) }}
          </button>
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
  </AppLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'

const rows = ref([])
const loading = ref(false)
const actingId = ref(null)

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
  return text.includes('GM') ? 'amber' : text.includes('RECOMMENDED') ? 'blue' : 'amber'
}

function shortType(type) {
  return String(type || '').replace('_INSPECTION', '').replaceAll('_', ' ')
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('en-IN')
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
    applyPagination(data)
  } finally {
    loading.value = false
  }
}

async function changeSize() {
  pagination.page = 1
  await loadPage()
}

async function goFirst() { pagination.page = 1; await loadPage() }
async function goPrev() { if (pagination.has_prev) { pagination.page -= 1; await loadPage() } }
async function goNext() { if (pagination.has_next) { pagination.page += 1; await loadPage() } }
async function goLast() { pagination.page = pagination.pages; await loadPage() }

async function recommend(i) {
  actingId.value = i.id
  try {
    let endpoint = '/reviews/' + i.id + '/line-manager'
    let payload = {
      action: 'RECOMMEND_PENALTY',
      comments: 'Reviewed and recommended from frontend.',
      recommended_penalty_amount: 0
    }

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
    if (rows.value.length === 0 && pagination.page > 1) {
      pagination.page -= 1
      await loadPage()
    }
  } finally {
    actingId.value = null
  }
}

onMounted(loadPage)
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

.mobile-list {
  display: none;
}

.full-width {
  width: 100%;
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
}
</style>
