<template>
  <AppLayout>
    <section class="card hero-panel">
      <div class="toolbar">
        <div>
          <h1>KPI-6 Score & Penalty Control</h1>
          <p class="hero-subtitle">Calculate monthly KPI-6 scores, verify station-level score split between SM and EIT inspections, and download final penalty reports.</p>
        </div>
        <button class="btn btn-secondary" @click="load">Refresh</button>
      </div>
      <div class="filter-grid section-gap">
        <label><span class="label">Billing Cycle ID</span><input class="input" v-model="billing_cycle_id" placeholder="1" /></label>
        <label><span class="label">Contract ID</span><input class="input" v-model="contract_id" placeholder="1" /></label>
        <button class="btn btn-primary" @click="calculate">Calculate Monthly KPI-6</button>
        <RouterLink class="btn btn-outline" to="/reports">Open PDF Reports</RouterLink>
      </div>
    </section>

    <div v-if="result" class="grid grid-3 section-gap">
      <StatCard label="Average Score" :value="`${result.average_score}%`" />
      <StatCard label="Penalty Applicable" :value="result.is_penalty_applicable ? 'Yes' : 'No'" />
      <StatCard label="Penalty Amount" :value="currency(result.penalty_amount)" />
    </div>

    <div class="grid grid-2 section-gap">
      <div class="card">
        <div class="card-title"><h2>Contract Scores</h2><span class="badge">Latest</span></div>
        <SimpleBarChart :items="scoreChart" suffix="%" />
      </div>
      <div class="card">
        <div class="card-title"><h2>Penalty Register</h2><span class="badge red">KPI-6</span></div>
        <div class="table-wrap mobile-cards">
          <table class="table">
            <thead><tr><th>Contract</th><th>Score</th><th>Bill</th><th>Penalty</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="p in penalties" :key="p.id">
                <td data-label="Contract">{{p.contract_id}}</td>
                <td data-label="Score">{{p.kpi_score}}%</td>
                <td data-label="Bill">{{currency(p.monthly_bill_value)}}</td>
                <td data-label="Penalty">{{currency(p.penalty_amount)}}</td>
                <td data-label="Status"><span class="badge amber">{{p.status}}</span></td>
              </tr>
              <tr v-if="!penalties.length"><td data-label="Penalty" colspan="5" class="muted">No penalty records found.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import StatCard from '../components/StatCard.vue'
import SimpleBarChart from '../components/SimpleBarChart.vue'
import { api } from '../services/api'

const billing_cycle_id = ref(1)
const contract_id = ref(1)
const result = ref(null)
const scores = ref([])
const penalties = ref([])
const scoreChart = computed(() => scores.value.map((r) => ({ label: `Contract ${r.contract_id} / Cycle ${r.billing_cycle_id}`, value: r.average_score || 0 })).slice(0, 8))

function currency(v){ return new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', maximumFractionDigits:0 }).format(v || 0) }
async function load(){ scores.value=(await api.get('/kpi/contract-scores')).data; penalties.value=(await api.get('/kpi/penalties')).data }
async function calculate(){ result.value=(await api.post('/kpi/calculate/monthly',{billing_cycle_id:Number(billing_cycle_id.value),contract_id:Number(contract_id.value)})).data; await load() }
onMounted(load)
</script>
