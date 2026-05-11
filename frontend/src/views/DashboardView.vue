
<template>
  <AppLayout>
    <section class="card hero-panel">
      <div class="toolbar">
        <div>
          <h1>Operations Cleanliness Command Dashboard</h1>
          <p class="hero-subtitle">Monitor KPI-6 inspections, station cleanliness trend, review backlog, contractor performance and generated penalties with weekly, monthly and yearly views.</p>
        </div>
        <div class="role-pill">{{ auth.user?.role }} view</div>
      </div>
      <div class="filter-grid section-gap">
        <label><span class="label">Period</span><select class="input" v-model="filters.period"><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="yearly">Yearly</option></select></label>
        <label><span class="label">From</span><input class="input" type="date" v-model="filters.from_date" /></label>
        <label><span class="label">To</span><input class="input" type="date" v-model="filters.to_date" /></label>
        <label><span class="label">Contract</span><select class="input" v-model="filters.contract_id"><option value="">All contracts</option><option v-for="c in master.contracts" :key="c.id" :value="c.id">{{ c.contract_code }}</option></select></label>
        <label><span class="label">Station</span><select class="input" v-model="filters.station_id"><option value="">All stations</option><option v-for="s in master.stations" :key="s.id" :value="s.id">{{ s.station_name }}</option></select></label>
        <button class="btn btn-primary" @click="load">Apply Filters</button>
      </div>
    </section>

    <div class="stat-grid section-gap">
      <StatCard label="Contracts" :value="analytics.summary?.contracts ?? 0" foot="Active contracts" />
      <StatCard label="Stations" :value="analytics.summary?.stations ?? 0" foot="Mapped stations" />
      <StatCard label="Inspections" :value="analytics.summary?.inspections ?? 0" foot="In selected period" />
      <StatCard label="Pending Reviews" :value="analytics.summary?.pending_reviews ?? 0" foot="Action required" />
      <StatCard label="Penalty Amount" :value="currency(analytics.summary?.penalty_amount || 0)" foot="Generated penalties" />
    </div>

    <div class="grid grid-3 section-gap">
      <div class="card" style="grid-column: span 2;">
        <div class="card-title"><h2>KPI-6 Score Trend</h2><span class="badge blue">{{ filters.period }}</span></div>
        <SimpleLineChart :items="analytics.score_trend || []" />
      </div>
      <div class="card">
        <div class="card-title"><h2>Latest Contract Score</h2><span class="badge" :class="scoreClass(latestScore)">{{ latestScore }}%</span></div>
        <DonutChart :value="latestScore" label="KPI-6">
          <p class="muted">Penalty threshold is 90%. Scores below threshold will be visible in penalty summary.</p>
          <RouterLink class="btn btn-secondary" to="/kpi">Open KPI module</RouterLink>
        </DonutChart>
      </div>
    </div>

    <div class="grid grid-2 section-gap">
      <div class="card">
        <div class="card-title"><h2>Station-wise Score</h2><span class="badge">Score %</span></div>
        <SimpleBarChart :items="analytics.station_scores || []" suffix="%" />
      </div>
      <div class="card">
        <div class="card-title"><h2>Inspection Volume</h2><span class="badge">Count</span></div>
        <SimpleBarChart :items="analytics.inspection_volume || []" />
      </div>
    </div>

    <div class="grid grid-2 section-gap">
      <div class="card">
        <div class="card-title"><h2>Grade Distribution</h2><span class="badge blue">A to F</span></div>
        <SimpleBarChart :items="analytics.grade_distribution || []" />
      </div>
      <div class="card">
        <div class="card-title"><h2>Report Downloads</h2><span class="badge green">PDF</span></div>
        <p class="muted">Download date-ranged inspection register as PDF. For detailed filters, open Reports & PDFs.</p>
        <div class="toolbar">
          <button class="btn btn-primary" @click="downloadRangePdf">Download Filtered PDF</button>
          <RouterLink class="btn btn-outline" to="/reports">Advanced Reports</RouterLink>
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
const master = ref({ contracts: [], stations: [] })
const filters = reactive({ period: 'monthly', from_date: '2026-01-01', to_date: '2026-05-31', contract_id: '', station_id: '' })
const latestScore = computed(() => Number(analytics.value.summary?.latest_score || analytics.value.score_trend?.at(-1)?.value || 0))
function scoreClass(v){ return v >= 90 ? 'green' : v >= 80 ? 'amber' : 'red' }
function currency(v){ return new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', maximumFractionDigits:0 }).format(v || 0) }
function params(){ return Object.fromEntries(Object.entries(filters).filter(([_,v]) => v !== '' && v !== null)) }
async function load(){ analytics.value = (await api.get('/dashboard/analytics', { params: params() })).data }
async function loadMaster(){ master.value = (await api.get('/master/bootstrap')).data }
async function downloadRangePdf(){ await downloadBlob('/reports/inspections/pdf', params(), 'inspection-register.pdf') }
onMounted(async()=>{ await loadMaster(); await load() })
</script>
<style scoped>
@media (max-width: 900px) { .grid-3 > .card[style] { grid-column: auto !important; } }
</style>
