<template>
  <AppLayout>
    <div class="master-page">
      <section class="hero-card">
        <div>
          <p class="eyebrow">Administration</p>
          <h1>Master Data Management</h1>
          <p>
            Manage operational data used by inspections: lines, stations, contractors, contracts,
            attributes, sub-areas and grading rules. Seed data remains only the first-time setup;
            production data should be maintained from this page by authorised users.
          </p>
        </div>
        <div class="role-box">
          <span>Current role</span>
          <strong>{{ data.current_role || auth.user?.role || 'UNKNOWN' }}</strong>
          <small :class="data.can_manage_master ? 'ok' : 'warn'">
            {{ data.can_manage_master ? 'Edit access enabled' : 'Read-only access' }}
          </small>
        </div>
      </section>

      <div v-if="!data.can_manage_master" class="notice warn-notice">
        Only SUPER_ADMIN / HK_CELL_ADMIN users can create, edit or deactivate master data.
        Other roles can view this page for reference.
      </div>

      <div v-if="message" class="notice success">{{ message }}</div>
      <div v-if="error" class="notice error">{{ error }}</div>

      <div class="tabs">
        <button v-for="tab in tabs" :key="tab.key" :class="['tab', { active: activeTab === tab.key }]" @click="activeTab = tab.key">
          {{ tab.label }}
        </button>
      </div>

      <section v-if="activeTab === 'lines'" class="card admin-section">
        <header><h2>Lines</h2><p>Create metro lines used for station mapping.</p></header>
        <form v-if="data.can_manage_master" class="form-grid" @submit.prevent="saveLine">
          <label>Line Code<input v-model.trim="lineForm.line_code" required placeholder="L3" /></label>
          <label>Line Name<input v-model.trim="lineForm.line_name" required placeholder="Blue Line" /></label>
          <div class="form-actions"><button class="btn" type="submit">{{ lineForm.id ? 'Update' : 'Add' }} Line</button><button class="btn btn-muted" type="button" @click="resetLine">Clear</button></div>
        </form>
        <DataTable :rows="data.lines" :columns="lineColumns" :can-manage="data.can_manage_master" @edit="editLine" @deactivate="id => deactivate('/master/lines', id)" />
      </section>

      <section v-if="activeTab === 'stations'" class="card admin-section">
        <header><h2>Stations</h2><p>Create stations and map each station to a line.</p></header>
        <form v-if="data.can_manage_master" class="form-grid" @submit.prevent="saveStation">
          <label>Station Code<input v-model.trim="stationForm.station_code" required placeholder="RKAS" /></label>
          <label>Station Name<input v-model.trim="stationForm.station_name" required placeholder="Rajiv Chowk" /></label>
          <label>Line<select v-model.number="stationForm.line_id" required><option disabled value="">Select line</option><option v-for="l in activeLines" :key="l.id" :value="l.id">{{ l.line_code }} - {{ l.line_name }}</option></select></label>
          <label>Latitude<input v-model.number="stationForm.latitude" type="number" step="0.000001" placeholder="28.6328" /></label>
          <label>Longitude<input v-model.number="stationForm.longitude" type="number" step="0.000001" placeholder="77.2197" /></label>
          <div class="form-actions"><button class="btn" type="submit">{{ stationForm.id ? 'Update' : 'Add' }} Station</button><button class="btn btn-muted" type="button" @click="resetStation">Clear</button></div>
        </form>
        <DataTable :rows="stationRows" :columns="stationColumns" :can-manage="data.can_manage_master" @edit="editStation" @deactivate="id => deactivate('/master/stations', id)" />
      </section>

      <section v-if="activeTab === 'contractors'" class="card admin-section">
        <header><h2>Contractors</h2><p>Create contractor agencies that own housekeeping contracts.</p></header>
        <form v-if="data.can_manage_master" class="form-grid" @submit.prevent="saveContractor">
          <label>Contractor Code<input v-model.trim="contractorForm.contractor_code" required placeholder="CTR001" /></label>
          <label>Contractor Name<input v-model.trim="contractorForm.contractor_name" required placeholder="ABC Housekeeping Pvt Ltd" /></label>
          <label>Contact Person<input v-model.trim="contractorForm.contact_person" /></label>
          <label>Mobile<input v-model.trim="contractorForm.mobile" /></label>
          <label>Email<input v-model.trim="contractorForm.email" type="email" /></label>
          <div class="form-actions"><button class="btn" type="submit">{{ contractorForm.id ? 'Update' : 'Add' }} Contractor</button><button class="btn btn-muted" type="button" @click="resetContractor">Clear</button></div>
        </form>
        <DataTable :rows="data.contractors" :columns="contractorColumns" :can-manage="data.can_manage_master" @edit="editContractor" @deactivate="id => deactivate('/master/contractors', id)" />
      </section>

      <section v-if="activeTab === 'contracts'" class="card admin-section">
        <header><h2>Contracts</h2><p>Create contracts and map stations to a contract.</p></header>
        <form v-if="data.can_manage_master" class="form-grid" @submit.prevent="saveContract">
          <label>Contract Code<input v-model.trim="contractForm.contract_code" required placeholder="DMRC/CHK-Ops-01/2026" /></label>
          <label>Tender No<input v-model.trim="contractForm.tender_no" /></label>
          <label>Contract Name<input v-model.trim="contractForm.contract_name" required /></label>
          <label>Contractor<select v-model.number="contractForm.contractor_id" required><option disabled value="">Select contractor</option><option v-for="c in activeContractors" :key="c.id" :value="c.id">{{ c.contractor_name }}</option></select></label>
          <label>Start Date<input v-model="contractForm.start_date" required type="date" /></label>
          <label>End Date<input v-model="contractForm.end_date" required type="date" /></label>
          <label>Extension End Date<input v-model="contractForm.extension_end_date" type="date" /></label>
          <label>Default Monthly Bill<input v-model.number="contractForm.monthly_bill_value_default" type="number" step="0.01" /></label>
          <label>Grading Scheme<select v-model.number="contractForm.grading_scheme_id" required><option disabled value="">Select scheme</option><option v-for="g in activeGradingSchemes" :key="g.id" :value="g.id">{{ g.name }}</option></select></label>
          <label>KPI-6 Threshold %<input v-model.number="contractForm.kpi6_threshold_percent" type="number" step="0.01" /></label>
          <label>KPI-6 Penalty %<input v-model.number="contractForm.kpi6_penalty_percent" type="number" step="0.01" /></label>
          <div class="form-actions"><button class="btn" type="submit">{{ contractForm.id ? 'Update' : 'Add' }} Contract</button><button class="btn btn-muted" type="button" @click="resetContract">Clear</button></div>
        </form>
        <div v-if="data.can_manage_master" class="mapping-box">
          <h3>Map Station to Contract</h3>
          <div class="mapping-grid">
            <select v-model.number="mapForm.contract_id"><option disabled value="">Select contract</option><option v-for="c in activeContracts" :key="c.id" :value="c.id">{{ c.contract_code }}</option></select>
            <select v-model.number="mapForm.station_id"><option disabled value="">Select station</option><option v-for="s in activeStations" :key="s.id" :value="s.id">{{ s.station_code }} - {{ s.station_name }}</option></select>
            <button class="btn" @click="mapStation" type="button">Map Station</button>
          </div>
        </div>
        <DataTable :rows="contractRows" :columns="contractColumns" :can-manage="data.can_manage_master" @edit="editContract" @deactivate="id => deactivate('/master/contracts', id)" />
      </section>

      <section v-if="activeTab === 'attributes'" class="card admin-section">
        <header><h2>Inspection Attributes</h2><p>Main categories selectable on the inspection-entry screen.</p></header>
        <form v-if="data.can_manage_master" class="form-grid" @submit.prevent="saveAttribute">
          <label>Code<input v-model.trim="attributeForm.code" required placeholder="ATTR_PLATFORM_AREA" /></label>
          <label>Name<input v-model.trim="attributeForm.name" required placeholder="Passenger Movement Area" /></label>
          <label>Sort Order<input v-model.number="attributeForm.sort_order" type="number" /></label>
          <label class="wide">Description<textarea v-model.trim="attributeForm.description" rows="2"></textarea></label>
          <div class="form-actions"><button class="btn" type="submit">{{ attributeForm.id ? 'Update' : 'Add' }} Attribute</button><button class="btn btn-muted" type="button" @click="resetAttribute">Clear</button></div>
        </form>
        <DataTable :rows="data.inspection_attributes" :columns="attributeColumns" :can-manage="data.can_manage_master" @edit="editAttribute" @deactivate="id => deactivate('/master/inspection-attributes', id)" />
      </section>

      <section v-if="activeTab === 'subareas'" class="card admin-section">
        <header><h2>Inspection Sub-areas</h2><p>Dependent dropdown values shown after selecting an attribute.</p></header>
        <form v-if="data.can_manage_master" class="form-grid" @submit.prevent="saveSubArea">
          <label>Attribute<select v-model.number="subAreaForm.attribute_id" required><option disabled value="">Select attribute</option><option v-for="a in activeAttributes" :key="a.id" :value="a.id">{{ a.name }}</option></select></label>
          <label>Code<input v-model.trim="subAreaForm.code" required placeholder="PLATFORM" /></label>
          <label>Name<input v-model.trim="subAreaForm.name" required placeholder="Platform" /></label>
          <label>Min Photos<input v-model.number="subAreaForm.photo_min_required" type="number" min="0" max="3" /></label>
          <label>Max Photos<input v-model.number="subAreaForm.photo_max_allowed" type="number" min="1" max="10" /></label>
          <label>Video Max Seconds<input v-model.number="subAreaForm.video_max_seconds" type="number" min="1" /></label>
          <label>Sort Order<input v-model.number="subAreaForm.sort_order" type="number" /></label>
          <label class="check"><input v-model="subAreaForm.video_required" type="checkbox" /> Video required</label>
          <label class="check"><input v-model="subAreaForm.allow_na" type="checkbox" /> Allow N/A</label>
          <div class="form-actions"><button class="btn" type="submit">{{ subAreaForm.id ? 'Update' : 'Add' }} Sub-area</button><button class="btn btn-muted" type="button" @click="resetSubArea">Clear</button></div>
        </form>
        <DataTable :rows="subAreaRows" :columns="subAreaColumns" :can-manage="data.can_manage_master" @edit="editSubArea" @deactivate="id => deactivate('/master/inspection-sub-areas', id)" />
      </section>

      <section v-if="activeTab === 'grading'" class="card admin-section">
        <header><h2>Grading Schemes</h2><p>Manage configurable grade percentages. Do not hardcode grade percentages in frontend/backend.</p></header>
        <form v-if="data.can_manage_master" class="form-grid" @submit.prevent="saveGradingScheme">
          <label>Scheme Code<input v-model.trim="gradingSchemeForm.code" required placeholder="KPI6_100_90" /></label>
          <label>Scheme Name<input v-model.trim="gradingSchemeForm.name" required placeholder="KPI-6 Tender Scale" /></label>
          <div class="form-actions"><button class="btn" type="submit">{{ gradingSchemeForm.id ? 'Update' : 'Add' }} Scheme</button><button class="btn btn-muted" type="button" @click="resetGradingScheme">Clear</button></div>
        </form>
        <DataTable :rows="data.grading_schemes" :columns="gradingSchemeColumns" :can-manage="data.can_manage_master" @edit="editGradingScheme" @deactivate="id => deactivate('/master/grading-schemes', id)" />

        <hr class="sep" />
        <h3>Grade Options</h3>
        <form v-if="data.can_manage_master" class="form-grid" @submit.prevent="saveGradingOption">
          <label>Scheme<select v-model.number="gradingOptionForm.scheme_id" required><option disabled value="">Select scheme</option><option v-for="g in activeGradingSchemes" :key="g.id" :value="g.id">{{ g.name }}</option></select></label>
          <label>Grade Code<input v-model.trim="gradingOptionForm.grade_code" required placeholder="A" /></label>
          <label>Label<input v-model.trim="gradingOptionForm.label" required placeholder="A - Excellent" /></label>
          <label>Percentage<input v-model.number="gradingOptionForm.percentage" required type="number" min="0" max="100" step="0.01" /></label>
          <label>Sort Order<input v-model.number="gradingOptionForm.sort_order" type="number" /></label>
          <div class="form-actions"><button class="btn" type="submit">{{ gradingOptionForm.id ? 'Update' : 'Add' }} Option</button><button class="btn btn-muted" type="button" @click="resetGradingOption">Clear</button></div>
        </form>
        <DataTable :rows="gradingOptionRows" :columns="gradingOptionColumns" :can-manage="data.can_manage_master" @edit="editGradingOption" @deactivate="id => deactivate('/master/grading-options', id)" />
      </section>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const activeTab = ref('lines')
const message = ref('')
const error = ref('')
const data = reactive({
  can_manage_master: false,
  current_role: '',
  lines: [], stations: [], contractors: [], contracts: [], contract_stations: [],
  grading_schemes: [], grading_options: [], inspection_attributes: [], inspection_sub_areas: []
})

const tabs = [
  { key: 'lines', label: 'Lines' },
  { key: 'stations', label: 'Stations' },
  { key: 'contractors', label: 'Contractors' },
  { key: 'contracts', label: 'Contracts' },
  { key: 'attributes', label: 'Attributes' },
  { key: 'subareas', label: 'Sub-areas' },
  { key: 'grading', label: 'Grading' }
]

const DataTable = defineComponent({
  props: { rows: Array, columns: Array, canManage: Boolean },
  emits: ['edit', 'deactivate'],
  setup(props, { emit }) {
    return () => h('div', { class: 'table-wrap' }, [
      h('table', { class: 'master-table' }, [
        h('thead', [h('tr', [
          ...props.columns.map(c => h('th', c.label)),
          ...(props.canManage ? [h('th', 'Actions')] : [])
        ])]),
        h('tbody', props.rows?.length ? props.rows.map(row => h('tr', { class: row.is_active === false ? 'inactive' : '' }, [
          ...props.columns.map(c => h('td', formatValue(c.render ? c.render(row) : row[c.key]))),
          ...(props.canManage ? [h('td', { class: 'actions' }, [
            h('button', { class: 'mini-btn', onClick: () => emit('edit', row) }, 'Edit'),
            h('button', { class: 'mini-btn danger', onClick: () => emit('deactivate', row.id) }, ctaDelete(row))
          ])] : [])
        ])) : [h('tr', [h('td', { colspan: props.columns.length + (props.canManage ? 1 : 0), class: 'empty' }, 'No records found')])])
      ])
    ])
  }
})

function formatValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}
function ctaDelete(row) { return row.is_active === false ? 'Inactive' : 'Deactivate' }
function activeOnly(list) { return list.filter(x => x.is_active !== false) }
const activeLines = computed(() => activeOnly(data.lines))
const activeStations = computed(() => activeOnly(data.stations))
const activeContractors = computed(() => activeOnly(data.contractors))
const activeContracts = computed(() => activeOnly(data.contracts))
const activeAttributes = computed(() => activeOnly(data.inspection_attributes))
const activeGradingSchemes = computed(() => activeOnly(data.grading_schemes))

const lineName = id => data.lines.find(x => x.id === id)?.line_name || id
const contractorName = id => data.contractors.find(x => x.id === id)?.contractor_name || id
const schemeName = id => data.grading_schemes.find(x => x.id === id)?.name || id
const attributeName = id => data.inspection_attributes.find(x => x.id === id)?.name || id

const lineColumns = [{ key:'line_code', label:'Code' }, { key:'line_name', label:'Name' }, { key:'is_active', label:'Active' }]
const stationColumns = [{ key:'station_code', label:'Code' }, { key:'station_name', label:'Name' }, { key:'line_name', label:'Line' }, { key:'is_active', label:'Active' }]
const contractorColumns = [{ key:'contractor_code', label:'Code' }, { key:'contractor_name', label:'Name' }, { key:'contact_person', label:'Contact' }, { key:'mobile', label:'Mobile' }, { key:'is_active', label:'Active' }]
const contractColumns = [{ key:'contract_code', label:'Code' }, { key:'contract_name', label:'Name' }, { key:'contractor_name', label:'Contractor' }, { key:'start_date', label:'Start' }, { key:'end_date', label:'End' }, { key:'is_active', label:'Active' }]
const attributeColumns = [{ key:'code', label:'Code' }, { key:'name', label:'Name' }, { key:'sort_order', label:'Sort' }, { key:'is_active', label:'Active' }]
const subAreaColumns = [{ key:'attribute_name', label:'Attribute' }, { key:'code', label:'Code' }, { key:'name', label:'Name' }, { key:'photo_min_required', label:'Min Photo' }, { key:'photo_max_allowed', label:'Max Photo' }, { key:'video_required', label:'Video Req.' }, { key:'is_active', label:'Active' }]
const gradingSchemeColumns = [{ key:'code', label:'Code' }, { key:'name', label:'Name' }, { key:'is_active', label:'Active' }]
const gradingOptionColumns = [{ key:'scheme_name', label:'Scheme' }, { key:'grade_code', label:'Grade' }, { key:'label', label:'Label' }, { key:'percentage', label:'%' }, { key:'sort_order', label:'Sort' }]

const stationRows = computed(() => data.stations.map(x => ({ ...x, line_name: lineName(x.line_id) })))
const contractRows = computed(() => data.contracts.map(x => ({ ...x, contractor_name: contractorName(x.contractor_id), grading_scheme_name: schemeName(x.grading_scheme_id) })))
const subAreaRows = computed(() => data.inspection_sub_areas.map(x => ({ ...x, attribute_name: attributeName(x.attribute_id) })))
const gradingOptionRows = computed(() => data.grading_options.map(x => ({ ...x, scheme_name: schemeName(x.scheme_id) })))

const lineForm = reactive({ id:null, line_code:'', line_name:'' })
const stationForm = reactive({ id:null, station_code:'', station_name:'', line_id:'', latitude:null, longitude:null })
const contractorForm = reactive({ id:null, contractor_code:'', contractor_name:'', contact_person:'', mobile:'', email:'' })
const contractForm = reactive({ id:null, contract_code:'', tender_no:'', contract_name:'', contractor_id:'', start_date:'', end_date:'', extension_end_date:'', monthly_bill_value_default:0, grading_scheme_id:'', kpi6_threshold_percent:90, kpi6_penalty_percent:5 })
const attributeForm = reactive({ id:null, code:'', name:'', description:'', sort_order:1 })
const subAreaForm = reactive({ id:null, attribute_id:'', code:'', name:'', photo_min_required:1, photo_max_allowed:3, video_required:false, video_max_seconds:15, allow_na:true, sort_order:1 })
const gradingSchemeForm = reactive({ id:null, code:'', name:'' })
const gradingOptionForm = reactive({ id:null, scheme_id:'', grade_code:'', label:'', percentage:100, sort_order:1 })
const mapForm = reactive({ contract_id:'', station_id:'' })

async function load() {
  const { data: payload } = await api.get('/master/bootstrap')
  Object.assign(data, payload)
}
function clearAlerts() { message.value = ''; error.value = '' }
function ok(msg) { message.value = msg; error.value = ''; setTimeout(() => { message.value = '' }, 2500) }
function fail(e) { error.value = e?.response?.data?.detail || e.message || 'Action failed'; message.value = '' }
function pick(obj, keys) { return keys.reduce((acc, key) => { acc[key] = obj[key] === '' ? null : obj[key]; return acc }, {}) }
async function save(url, form, keys, reset) {
  clearAlerts()
  try {
    const payload = pick(form, keys)
    if (form.id) await api.put(`${url}/${form.id}`, payload)
    else await api.post(url, payload)
    reset(); await load(); ok('Master data saved successfully.')
  } catch (e) { fail(e) }
}
async function deactivate(url, id) {
  if (!confirm('Deactivate this record? Old inspections will remain linked, but it will not appear as active.')) return
  clearAlerts()
  try { await api.delete(`${url}/${id}`); await load(); ok('Record deactivated.') } catch (e) { fail(e) }
}

const lineKeys = ['line_code', 'line_name']
function resetLine(){ Object.assign(lineForm, { id:null, line_code:'', line_name:'' }) }
function editLine(x){ Object.assign(lineForm, x); activeTab.value='lines' }
function saveLine(){ save('/master/lines', lineForm, lineKeys, resetLine) }

const stationKeys = ['station_code', 'station_name', 'line_id', 'latitude', 'longitude']
function resetStation(){ Object.assign(stationForm, { id:null, station_code:'', station_name:'', line_id:'', latitude:null, longitude:null }) }
function editStation(x){ Object.assign(stationForm, x); activeTab.value='stations' }
function saveStation(){ save('/master/stations', stationForm, stationKeys, resetStation) }

const contractorKeys = ['contractor_code', 'contractor_name', 'contact_person', 'mobile', 'email']
function resetContractor(){ Object.assign(contractorForm, { id:null, contractor_code:'', contractor_name:'', contact_person:'', mobile:'', email:'' }) }
function editContractor(x){ Object.assign(contractorForm, x); activeTab.value='contractors' }
function saveContractor(){ save('/master/contractors', contractorForm, contractorKeys, resetContractor) }

const contractKeys = ['contract_code', 'tender_no', 'contract_name', 'contractor_id', 'start_date', 'end_date', 'extension_end_date', 'monthly_bill_value_default', 'grading_scheme_id', 'kpi6_threshold_percent', 'kpi6_penalty_percent']
function resetContract(){ Object.assign(contractForm, { id:null, contract_code:'', tender_no:'', contract_name:'', contractor_id:'', start_date:'', end_date:'', extension_end_date:'', monthly_bill_value_default:0, grading_scheme_id:'', kpi6_threshold_percent:90, kpi6_penalty_percent:5 }) }
function editContract(x){ Object.assign(contractForm, x); activeTab.value='contracts' }
function saveContract(){ save('/master/contracts', contractForm, contractKeys, resetContract) }
async function mapStation() {
  clearAlerts()
  if (!mapForm.contract_id || !mapForm.station_id) { error.value = 'Select both contract and station.'; return }
  try { await api.post(`/master/contracts/${mapForm.contract_id}/stations`, { station_id: mapForm.station_id }); mapForm.station_id=''; await load(); ok('Station mapped to contract.') } catch(e) { fail(e) }
}

const attributeKeys = ['code', 'name', 'description', 'sort_order']
function resetAttribute(){ Object.assign(attributeForm, { id:null, code:'', name:'', description:'', sort_order:1 }) }
function editAttribute(x){ Object.assign(attributeForm, x); activeTab.value='attributes' }
function saveAttribute(){ save('/master/inspection-attributes', attributeForm, attributeKeys, resetAttribute) }

const subAreaKeys = ['attribute_id', 'code', 'name', 'photo_min_required', 'photo_max_allowed', 'video_required', 'video_max_seconds', 'allow_na', 'sort_order']
function resetSubArea(){ Object.assign(subAreaForm, { id:null, attribute_id:'', code:'', name:'', photo_min_required:1, photo_max_allowed:3, video_required:false, video_max_seconds:15, allow_na:true, sort_order:1 }) }
function editSubArea(x){ Object.assign(subAreaForm, x); activeTab.value='subareas' }
function saveSubArea(){ save('/master/inspection-sub-areas', subAreaForm, subAreaKeys, resetSubArea) }

const gradingSchemeKeys = ['code', 'name']
function resetGradingScheme(){ Object.assign(gradingSchemeForm, { id:null, code:'', name:'' }) }
function editGradingScheme(x){ Object.assign(gradingSchemeForm, x); activeTab.value='grading' }
function saveGradingScheme(){ save('/master/grading-schemes', gradingSchemeForm, gradingSchemeKeys, resetGradingScheme) }

const gradingOptionKeys = ['scheme_id', 'grade_code', 'label', 'percentage', 'sort_order']
function resetGradingOption(){ Object.assign(gradingOptionForm, { id:null, scheme_id:'', grade_code:'', label:'', percentage:100, sort_order:1 }) }
function editGradingOption(x){ Object.assign(gradingOptionForm, x); activeTab.value='grading' }
function saveGradingOption(){ save('/master/grading-options', gradingOptionForm, gradingOptionKeys, resetGradingOption) }

onMounted(load)
</script>

<style scoped>
.master-page { display:grid; gap:18px; }
.hero-card { display:flex; justify-content:space-between; gap:18px; padding:24px; border-radius:26px; background:linear-gradient(135deg,#061a44,#0c3a8f); color:white; box-shadow:0 24px 60px rgba(8,31,80,.18); }
.hero-card h1 { margin:4px 0 8px; font-size:32px; }
.hero-card p { margin:0; max-width:850px; color:#dbeafe; line-height:1.6; }
.eyebrow { text-transform:uppercase; letter-spacing:.14em; color:#bfdbfe !important; font-size:12px; font-weight:900; }
.role-box { min-width:210px; border:1px solid rgba(255,255,255,.18); background:rgba(255,255,255,.10); border-radius:20px; padding:16px; align-self:start; }
.role-box span, .role-box small { display:block; color:#dbeafe; }
.role-box strong { display:block; font-size:20px; margin:6px 0; }
.ok { color:#bbf7d0 !important; }
.warn { color:#fde68a !important; }
.notice { padding:12px 14px; border-radius:14px; font-weight:800; }
.success { background:#dcfce7; color:#166534; border:1px solid #86efac; }
.error { background:#fee2e2; color:#991b1b; border:1px solid #fecaca; }
.warn-notice { background:#fff7ed; color:#9a3412; border:1px solid #fed7aa; }
.tabs { display:flex; gap:8px; flex-wrap:wrap; }
.tab { border:1px solid #dbe3f0; background:white; border-radius:999px; padding:10px 14px; cursor:pointer; font-weight:900; color:#334155; }
.tab.active { background:#092b6f; color:white; border-color:#092b6f; }
.admin-section header { margin-bottom:16px; }
.admin-section header h2 { margin-bottom:4px; }
.admin-section header p { color:#64748b; margin:0; }
.form-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; padding:16px; margin-bottom:18px; border-radius:20px; background:#f8fafc; border:1px solid #e2e8f0; }
.form-grid label { display:grid; gap:6px; font-size:13px; font-weight:900; color:#334155; }
.form-grid .wide { grid-column:1 / -1; }
input, select, textarea { width:100%; border:1px solid #cbd5e1; border-radius:12px; padding:10px 12px; background:white; font:inherit; }
textarea { resize:vertical; }
.check { display:flex !important; align-items:center; gap:8px !important; padding-top:26px; }
.check input { width:auto; }
.form-actions { display:flex; align-items:end; gap:8px; flex-wrap:wrap; }
.btn { border:0; border-radius:12px; padding:10px 14px; background:#0b3a8f; color:white; font-weight:900; cursor:pointer; }
.btn-muted { background:#e2e8f0; color:#334155; }
.mapping-box { padding:14px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:18px; margin-bottom:16px; }
.mapping-box h3 { margin:0 0 10px; }
.mapping-grid { display:grid; grid-template-columns:1fr 1fr auto; gap:10px; }
.table-wrap { overflow:auto; border:1px solid #e2e8f0; border-radius:18px; }
.master-table { width:100%; border-collapse:collapse; background:white; min-width:720px; }
th { background:#f1f5f9; color:#334155; font-size:12px; text-align:left; text-transform:uppercase; letter-spacing:.04em; }
th, td { padding:11px 12px; border-bottom:1px solid #e2e8f0; vertical-align:top; }
tr.inactive td { color:#94a3b8; background:#f8fafc; }
.actions { display:flex; gap:8px; }
.mini-btn { border:1px solid #cbd5e1; background:white; color:#0f172a; border-radius:10px; padding:7px 10px; font-weight:900; cursor:pointer; }
.mini-btn.danger { color:#991b1b; border-color:#fecaca; background:#fff1f2; }
.empty { text-align:center; color:#64748b; padding:28px !important; }
.sep { border:0; border-top:1px solid #e2e8f0; margin:22px 0; }
@media (max-width: 980px) { .hero-card { display:block; } .role-box { margin-top:14px; } .form-grid { grid-template-columns:1fr; } .mapping-grid { grid-template-columns:1fr; } }
</style>
