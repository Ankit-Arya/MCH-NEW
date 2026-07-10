<template>
  <AppLayout>
    <section class="card hero-panel">
      <div class="hero-row">
        <div>
          <h1>Weekly Station-wise Inspection Compliance</h1>
          <p class="hero-subtitle">
            Shows whether every mapped SM/EIT has completed the required weekly inspections for every station in your hierarchy.
          </p>
        </div>
        <button class="btn btn-primary" type="button" @click="load" :disabled="loading">
          {{ loading ? 'Refreshing...' : 'Refresh' }}
        </button>
      </div>
    </section>

    <section v-if="error" class="card section-gap error-card">
      {{ error }}
    </section>

    <section class="summary-grid section-gap" v-if="summary">
      <div class="summary-card" :class="summary.total_remaining ? 'attention' : 'ok'">
        <span>Total remaining</span>
        <strong>{{ summary.total_remaining }}</strong>
        <small>pending inspections</small>
      </div>
      <div class="summary-card">
        <span>Target</span>
        <strong>{{ summary.total_required }}</strong>
        <small>station-wise required</small>
      </div>
      <div class="summary-card">
        <span>Completed</span>
        <strong>{{ summary.total_completed }}</strong>
        <small>capped to target</small>
      </div>
      <div class="summary-card" :class="summary.pending_rows ? 'attention' : 'ok'">
        <span>Pending rows</span>
        <strong>{{ summary.pending_rows }}</strong>
        <small>SM/EIT + station rows</small>
      </div>
    </section>

    <section class="card section-gap">
      <div class="toolbar-grid">
        <label>
          <span class="label">Search</span>
          <input class="input" v-model.trim="search" placeholder="Search SM/EIT, station, LM, DGM, GM" />
        </label>
        <label>
          <span class="label">Status</span>
          <select class="input" v-model="statusFilter">
            <option value="ALL">All rows</option>
            <option value="PENDING">Pending only</option>
            <option value="COMPLETE">Complete only</option>
            <option value="NO_STATION_MAPPING">No station mapping</option>
          </select>
        </label>
        <label>
          <span class="label">Role</span>
          <select class="input" v-model="roleFilter">
            <option value="ALL">All roles</option>
            <option value="STATION_MANAGER">Station Manager</option>
            <option value="EIT_MEMBER">EIT</option>
          </select>
        </label>
      </div>

      <div class="week-strip" v-if="weekStart && weekEnd">
        <strong>Week:</strong>
        <span>{{ formatDate(weekStart) }} to {{ formatDate(weekEnd) }}</span>
        <span class="muted">{{ filteredRows.length }} row{{ filteredRows.length === 1 ? '' : 's' }} shown</span>
      </div>

      <div class="table-wrap compliance-table-wrap">
        <table class="table compliance-table">
          <thead>
            <tr>
              <th>Inspector</th>
              <th>Station</th>
              <th>Target</th>
              <th>Done</th>
              <th>Remaining</th>
              <th>Status</th>
              <th>Line Manager</th>
              <th>DGM</th>
              <th>GM/Ops</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRows" :key="`${row.inspector_id}-${row.station_id || 'none'}`" :class="{ pending: row.remaining > 0, complete: row.is_complete }">
              <td>
                <strong>{{ row.inspector_name }}</strong><br />
                <span class="muted small-text">{{ row.username }} · {{ row.emp_number || 'No emp no' }} · {{ row.role_label }}</span>
              </td>
              <td>
                <strong>{{ row.station_name }}</strong><br />
                <span class="muted small-text">{{ row.station_code || '-' }}</span>
              </td>
              <td>{{ row.required }}</td>
              <td>{{ row.completed }}</td>
              <td><strong>{{ row.remaining }}</strong></td>
              <td><span class="badge" :class="statusClass(row)">{{ statusLabel(row.status) }}</span></td>
              <td>{{ row.line_manager || '-' }}</td>
              <td>{{ row.dgm || '-' }}</td>
              <td>{{ row.gm || '-' }}</td>
            </tr>
            <tr v-if="!filteredRows.length">
              <td colspan="9" class="muted">No rows match the selected filters.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'

const loading = ref(false)
const error = ref('')
const rows = ref([])
const summary = ref(null)
const weekStart = ref('')
const weekEnd = ref('')
const search = ref('')
const statusFilter = ref('PENDING')
const roleFilter = ref('ALL')

const filteredRows = computed(() => {
  const query = search.value.toLowerCase()
  return rows.value.filter((row) => {
    if (statusFilter.value !== 'ALL' && row.status !== statusFilter.value) return false
    if (roleFilter.value !== 'ALL' && row.role !== roleFilter.value) return false
    if (!query) return true
    return [
      row.inspector_name,
      row.username,
      row.emp_number,
      row.role_label,
      row.station_name,
      row.station_code,
      row.line_manager,
      row.dgm,
      row.gm,
      row.message
    ].filter(Boolean).some((value) => String(value).toLowerCase().includes(query))
  })
})

function formatDate(value) {
  if (!value) return '-'
  if (/^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
    const [year, month, day] = String(value).split('-')
    return `${day}/${month}/${year}`
  }
  return new Date(value).toLocaleDateString('en-IN')
}

function statusLabel(status) {
  if (status === 'COMPLETE') return 'Complete'
  if (status === 'PENDING') return 'Pending'
  if (status === 'NO_STATION_MAPPING') return 'No station mapping'
  return String(status || '-')
}

function statusClass(row) {
  if (row.status === 'COMPLETE') return 'green'
  if (row.status === 'NO_STATION_MAPPING') return 'red'
  return 'amber'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/weekly-compliance/report')
    rows.value = data.rows || []
    summary.value = data.summary || null
    weekStart.value = data.week_start || ''
    weekEnd.value = data.week_end || ''
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Unable to load weekly compliance report.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.section-gap { margin-top: 18px; }
.hero-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.hero-subtitle { margin-top: 8px; max-width: 840px; color: #64748b; line-height: 1.5; }
.error-card { color: #991b1b; background: #fef2f2; border-color: #fecaca; font-weight: 800; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.summary-card { border: 1px solid #dbe3f0; border-radius: 20px; background: white; padding: 16px; box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06); }
.summary-card span { display: block; color: #64748b; font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: .05em; }
.summary-card strong { display: block; margin-top: 6px; color: #0f172a; font-size: 32px; line-height: 1; }
.summary-card small { display: block; margin-top: 7px; color: #475569; font-weight: 800; }
.summary-card.attention { border-color: #fcd34d; background: #fffbeb; }
.summary-card.ok { border-color: #bbf7d0; background: #f0fdf4; }
.toolbar-grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 14px; align-items: end; }
.week-strip { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 16px 0; color: #17345c; }
.compliance-table-wrap { overflow-x: auto; }
.compliance-table { min-width: 1160px; }
.compliance-table th, .compliance-table td { vertical-align: top; }
.compliance-table tbody tr.pending { background: #fffbeb; }
.compliance-table tbody tr.complete { background: #f8fffb; }
.small-text { font-size: 12px; }
.badge.green { background: #dcfce7; color: #166534; }
.badge.amber { background: #fef3c7; color: #92400e; }
.badge.red { background: #fee2e2; color: #991b1b; }
@media (max-width: 900px) {
  .hero-row { display: grid; }
  .summary-grid, .toolbar-grid { grid-template-columns: 1fr; }
}
</style>
