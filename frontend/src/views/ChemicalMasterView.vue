<template>
  <AppLayout>
    <section class="card hero-panel chemical-hero">
      <div>
        <p class="section-kicker">Master Data</p>
        <h1>Chemicals & Consumables Mapping</h1>
        <p class="hero-subtitle">Maintain editable chemical master data and station-wise required quantities for chemical KPI inspections.</p>
      </div>
      <button class="btn btn-secondary" type="button" @click="loadAll" :disabled="loading">{{ loading ? 'Refreshing...' : 'Refresh' }}</button>
    </section>

    <section v-if="message" class="card section-gap notice success-text">{{ message }}</section>
    <section v-if="error" class="card section-gap notice error">{{ error }}</section>

    <div class="chemical-layout section-gap">
      <section class="card">
        <div class="card-title"><h2>Chemical list</h2><p class="muted">Create/edit chemicals and units.</p></div>
        <form class="form-grid" @submit.prevent="saveChemical">
          <label><span class="label">Code</span><input class="input" v-model.trim="chemicalForm.code" required placeholder="PHENYL" /></label>
          <label><span class="label">Name</span><input class="input" v-model.trim="chemicalForm.name" required placeholder="Phenyl" /></label>
          <label><span class="label">Unit</span><input class="input" v-model.trim="chemicalForm.unit" required placeholder="Ltr" /></label>
          <label><span class="label">Default required qty</span><input class="input" v-model.number="chemicalForm.default_required_quantity" type="number" min="0" step="0.01" /></label>
          <label><span class="label">Sort</span><input class="input" v-model.number="chemicalForm.sort_order" type="number" min="1" /></label>
          <label class="wide"><span class="label">Description</span><textarea class="input" v-model.trim="chemicalForm.description" rows="2"></textarea></label>
          <div class="form-actions"><button class="btn btn-primary" type="submit">{{ chemicalForm.id ? 'Update chemical' : 'Add chemical' }}</button><button class="btn btn-muted" type="button" @click="resetChemical">Clear</button></div>
        </form>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Code</th><th>Name</th><th>Unit</th><th>Default qty</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              <tr v-for="c in chemicals" :key="c.id"><td>{{ c.code }}</td><td>{{ c.name }}</td><td>{{ c.unit }}</td><td>{{ c.default_required_quantity }}</td><td>{{ c.is_active ? 'Active' : 'Inactive' }}</td><td><button class="btn btn-sm btn-outline" @click="editChemical(c)">Edit</button></td></tr>
              <tr v-if="!chemicals.length"><td colspan="6" class="muted">No chemicals configured.</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card">
        <div class="card-title"><h2>Station-wise requirement</h2><p class="muted">Map each station to required chemical quantity.</p></div>
        <label><span class="label">Station</span><select class="input" v-model.number="selectedStationId" @change="loadRequirements"><option disabled value="">Select station</option><option v-for="s in stations" :key="s.id" :value="s.id">{{ s.station_code }} — {{ s.station_name }}</option></select></label>
        <form class="form-grid section-gap" @submit.prevent="saveRequirement">
          <label><span class="label">Chemical</span><select class="input" v-model.number="requirementForm.chemical_id" required><option disabled value="">Select chemical</option><option v-for="c in activeChemicals" :key="c.id" :value="c.id">{{ c.code }} — {{ c.name }}</option></select></label>
          <label><span class="label">Required quantity</span><input class="input" v-model.number="requirementForm.required_quantity" required type="number" min="0" step="0.01" /></label>
          <label><span class="label">Unit override</span><input class="input" v-model.trim="requirementForm.unit" placeholder="Optional" /></label>
          <label class="wide"><span class="label">Remarks</span><textarea class="input" v-model.trim="requirementForm.remarks" rows="2"></textarea></label>
          <div class="form-actions"><button class="btn btn-primary" type="submit" :disabled="!selectedStationId">{{ requirementForm.id ? 'Update requirement' : 'Map requirement' }}</button><button class="btn btn-muted" type="button" @click="resetRequirement">Clear</button></div>
        </form>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Chemical</th><th>Required</th><th>Unit</th><th>Remarks</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              <tr v-for="r in requirements" :key="r.id"><td>{{ r.chemical_code }} — {{ r.chemical_name }}</td><td>{{ r.required_quantity }}</td><td>{{ r.unit }}</td><td>{{ r.remarks || '-' }}</td><td>{{ r.is_active ? 'Active' : 'Inactive' }}</td><td><button class="btn btn-sm btn-outline" @click="editRequirement(r)">Edit</button></td></tr>
              <tr v-if="!requirements.length"><td colspan="6" class="muted">No station chemical requirements mapped.</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'

const loading = ref(false)
const message = ref('')
const error = ref('')
const chemicals = ref([])
const stations = ref([])
const requirements = ref([])
const selectedStationId = ref('')
const chemicalForm = reactive({ id: null, code: '', name: '', unit: 'Ltr/Kg/No', default_required_quantity: 0, description: '', sort_order: 1 })
const requirementForm = reactive({ id: null, chemical_id: '', required_quantity: 0, unit: '', remarks: '' })
const activeChemicals = computed(() => chemicals.value.filter((c) => c.is_active !== false))

function ok(text){ error.value = ''; message.value = text; setTimeout(() => { message.value = '' }, 2500) }
function fail(e){ message.value = ''; error.value = e?.response?.data?.detail || e?.message || 'Action failed' }
function resetChemical(){ Object.assign(chemicalForm, { id: null, code: '', name: '', unit: 'Ltr/Kg/No', default_required_quantity: 0, description: '', sort_order: 1 }) }
function resetRequirement(){ Object.assign(requirementForm, { id: null, chemical_id: '', required_quantity: 0, unit: '', remarks: '' }) }
function editChemical(c){ Object.assign(chemicalForm, { ...c }) }
function editRequirement(r){ Object.assign(requirementForm, { id: r.id, chemical_id: r.chemical_id, required_quantity: r.required_quantity, unit: r.unit || '', remarks: r.remarks || '' }) }

async function loadAll(){
  loading.value = true
  try {
    const [chemRes, bootRes] = await Promise.all([
      api.get('/kpi-chemicals/chemicals', { params: { include_inactive: true } }),
      api.get('/master/bootstrap')
    ])
    chemicals.value = chemRes.data || []
    stations.value = bootRes.data?.stations || []
    if (selectedStationId.value) await loadRequirements()
  } catch(e) { fail(e) } finally { loading.value = false }
}
async function loadRequirements(){
  if (!selectedStationId.value) { requirements.value = []; return }
  try {
    const { data } = await api.get(`/kpi-chemicals/stations/${selectedStationId.value}/requirements`, { params: { include_inactive: true } })
    requirements.value = data || []
  } catch(e) { fail(e) }
}
async function saveChemical(){
  try {
    const payload = { code: chemicalForm.code, name: chemicalForm.name, unit: chemicalForm.unit, default_required_quantity: Number(chemicalForm.default_required_quantity || 0), description: chemicalForm.description || null, sort_order: Number(chemicalForm.sort_order || 1) }
    if (chemicalForm.id) await api.put(`/kpi-chemicals/chemicals/${chemicalForm.id}`, payload)
    else await api.post('/kpi-chemicals/chemicals', payload)
    resetChemical(); await loadAll(); ok('Chemical saved.')
  } catch(e) { fail(e) }
}
async function saveRequirement(){
  if (!selectedStationId.value) { error.value = 'Select station first'; return }
  try {
    const payload = { chemical_id: Number(requirementForm.chemical_id), required_quantity: Number(requirementForm.required_quantity || 0), unit: requirementForm.unit || null, remarks: requirementForm.remarks || null }
    if (requirementForm.id) await api.put(`/kpi-chemicals/station-requirements/${requirementForm.id}`, payload)
    else await api.post(`/kpi-chemicals/stations/${selectedStationId.value}/requirements`, payload)
    resetRequirement(); await loadRequirements(); ok('Station requirement saved.')
  } catch(e) { fail(e) }
}

onMounted(loadAll)
</script>

<style scoped>
.chemical-hero { display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }
.chemical-layout { display:grid; grid-template-columns:minmax(360px, 1fr) minmax(420px, 1.1fr); gap:18px; align-items:start; }
.form-grid { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:12px; }
.wide { grid-column:1/-1; }
.form-actions { grid-column:1/-1; display:flex; gap:10px; flex-wrap:wrap; }
.notice { font-weight:900; }
.error { color:#dc2626; font-weight:800; }
.success-text { color:#166534; font-weight:900; }
@media(max-width:1000px){ .chemical-layout, .form-grid, .chemical-hero { grid-template-columns:1fr; display:grid; } }
</style>
