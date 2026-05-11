
<template>
  <AppLayout>
    <section class="card hero-panel">
      <h1>Inspection Reports & PDF Register</h1>
      <p class="hero-subtitle">Search inspections by date range, Station Manager/EIT, station, contract, inspection type and status. Download single inspection PDF or a consolidated register PDF for record keeping.</p>
      <div class="filter-grid section-gap">
        <label><span class="label">From</span><input class="input" type="date" v-model="filters.from_date" /></label>
        <label><span class="label">To</span><input class="input" type="date" v-model="filters.to_date" /></label>
        <label><span class="label">Contract</span><select class="input" v-model="filters.contract_id"><option value="">All</option><option v-for="c in master.contracts" :key="c.id" :value="c.id">{{ c.contract_code }}</option></select></label>
        <label><span class="label">Station</span><select class="input" v-model="filters.station_id"><option value="">All</option><option v-for="s in master.stations" :key="s.id" :value="s.id">{{ s.station_name }}</option></select></label>
        <label><span class="label">SM / EIT</span><select class="input" v-model="filters.submitted_by"><option value="">All</option><option v-for="u in master.users" :key="u.id" :value="u.id">{{ u.name }}</option></select></label>
        <label><span class="label">Type</span><select class="input" v-model="filters.inspection_type"><option value="">All</option><option>SM_INSPECTION</option><option>EIT_INSPECTION</option><option>SPECIAL_INSPECTION</option></select></label>
      </div>
      <div class="toolbar section-gap">
        <button class="btn btn-primary" @click="search">Search</button>
        <button class="btn btn-secondary" @click="downloadRegister">Download Date Range PDF</button>
        <button class="btn btn-outline" @click="reset">Reset</button>
      </div>
    </section>

    <section class="card section-gap">
      <div class="card-title">
        <h2>Inspection Register</h2>
        <span class="badge blue">{{ rows.length }} records</span>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Inspection No</th><th>Date</th><th>Station</th><th>Contract</th><th>Inspector</th><th>Type</th><th>Status</th><th>Score</th><th>PDF</th></tr></thead>
          <tbody>
            <tr v-for="r in rows" :key="r.id">
              <td><strong>{{ r.inspection_no }}</strong></td>
              <td>{{ r.inspection_date }}</td>
              <td>{{ r.station_name }}</td>
              <td>{{ r.contract_code }}</td>
              <td>{{ r.submitted_by_name }}</td>
              <td><span class="badge">{{ r.inspection_type }}</span></td>
              <td><span class="badge" :class="statusClass(r.status)">{{ r.status }}</span></td>
              <td><strong>{{ r.score }}%</strong></td>
              <td><button class="btn btn-sm btn-primary" @click="downloadSingle(r.id, r.inspection_no)">PDF</button></td>
            </tr>
            <tr v-if="!rows.length"><td colspan="9" class="muted">No inspections found.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </AppLayout>
</template>
<script setup>
import { onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api, downloadBlob } from '../services/api'
const rows = ref([])
const master = ref({ contracts: [], stations: [], users: [] })
const defaultFilters = () => ({ from_date:'2026-01-01', to_date:'2026-05-31', contract_id:'', station_id:'', submitted_by:'', inspection_type:'' })
const filters = reactive(defaultFilters())
function params(){ return Object.fromEntries(Object.entries(filters).filter(([_,v]) => v !== '' && v !== null)) }
function statusClass(s){ return String(s).includes('APPROVED') || String(s).includes('CLOSED') ? 'green' : String(s).includes('REVIEW') || String(s).includes('RECOMMENDED') ? 'amber' : 'blue' }
async function loadMaster(){ master.value = (await api.get('/master/bootstrap')).data }
async function search(){ rows.value = (await api.get('/reports/inspections/search', { params: params() })).data }
async function downloadSingle(id, no){ await downloadBlob(`/reports/inspection/${id}/pdf`, {}, `${no}.pdf`) }
async function downloadRegister(){ await downloadBlob('/reports/inspections/pdf', params(), 'inspection-register.pdf') }
async function reset(){ Object.assign(filters, defaultFilters()); await search() }
onMounted(async()=>{ await loadMaster(); await search() })
</script>
