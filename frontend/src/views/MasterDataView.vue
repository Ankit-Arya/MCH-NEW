<template>
  <AppLayout>
    <div class="master-page">
      <section class="card hero-panel master-hero">
        <div class="toolbar hero-toolbar">
          <div>
            <p class="section-kicker">Administration</p>
            <h1>Master Data Management</h1>
            <p class="hero-subtitle">
              Maintain the reference data that drives inspections, KPI calculations and reports.
              Each setup area is separated so users do not have to work through one crowded screen.
            </p>
          </div>

          <div class="hero-actions">
            <span class="role-pill">{{ currentRole }}</span>
            <span class="access-pill" :class="data.can_manage_master ? 'editable' : 'readonly'">
              {{ data.can_manage_master ? 'Edit access enabled' : 'Read-only access' }}
            </span>
            <button class="btn btn-secondary" type="button" :disabled="loading" @click="load">
              {{ loading ? 'Refreshing...' : 'Refresh data' }}
            </button>
          </div>
        </div>

        <div class="summary-grid">
          <article v-for="item in summaryItems" :key="item.label" class="summary-card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <small>{{ item.foot }}</small>
          </article>
        </div>
      </section>

      <section v-if="!data.can_manage_master" class="card section-gap notice-card warning-card">
        <strong>Read-only mode</strong>
        <span>Only Super Admin and HK Cell Admin users can create, edit or deactivate master data. Other users can review setup data for reference.</span>
      </section>

      <section v-if="message" class="card section-gap notice-card success-card">
        <strong>Saved</strong>
        <span>{{ message }}</span>
      </section>

      <section v-if="error" class="card section-gap notice-card error-card">
        <strong>Action failed</strong>
        <span>{{ error }}</span>
      </section>

      <section class="card section-gap master-workbench">
        <aside class="master-nav">
          <div class="nav-heading">
            <h2>Setup areas</h2>
            <p>Choose one master-data area at a time.</p>
          </div>

          <button
            v-for="section in sections"
            :key="section.key"
            type="button"
            class="nav-item"
            :class="{ active: activeTab === section.key }"
            @click="setTab(section.key)"
          >
            <span class="nav-icon">{{ section.icon }}</span>
            <span class="nav-copy">
              <strong>{{ section.label }}</strong>
              <small>{{ section.desc }}</small>
            </span>
            <span class="nav-count">{{ countFor(section.key) }}</span>
          </button>
        </aside>

        <main class="master-content">
          <div class="content-header">
            <div>
              <p class="section-kicker">{{ activeSection.group }}</p>
              <h2>{{ activeSection.title }}</h2>
              <p class="muted small-text">{{ activeSection.help }}</p>
            </div>

            <div class="content-tools">
              <input
                class="input"
                v-model.trim="searchQuery"
                :placeholder="`Search ${activeSection.label.toLowerCase()}`"
              />
              <select class="input status-select" v-model="recordStatusFilter">
                <option value="ALL">All status</option>
                <option value="ACTIVE">Active only</option>
                <option value="INACTIVE">Inactive only</option>
              </select>
              <button v-if="data.can_manage_master" class="btn btn-outline" type="button" @click="clearCurrentForm">
                New / Clear
              </button>
            </div>
          </div>

          <div v-if="data.can_manage_master" class="editor-shell">
            <div class="editor-title">
              <div>
                <p class="section-kicker">{{ editingLabel }}</p>
                <h3>{{ editorTitle }}</h3>
              </div>
              <span class="edit-mode-pill">{{ hasActiveEdit ? 'Editing existing record' : 'Creating new record' }}</span>
            </div>

            <form v-if="activeTab === 'lines'" class="form-grid compact-form" @submit.prevent="saveLine">
              <label><span class="label">Line code</span><input class="input" v-model.trim="lineForm.line_code" required placeholder="L3" /></label>
              <label><span class="label">Line name</span><input class="input" v-model.trim="lineForm.line_name" required placeholder="Blue Line" /></label>
              <div class="form-actions"><button class="btn btn-primary" type="submit">{{ lineForm.id ? 'Update line' : 'Add line' }}</button><button class="btn btn-muted" type="button" @click="resetLine">Clear</button></div>
            </form>

            <form v-else-if="activeTab === 'stations'" class="form-grid" @submit.prevent="saveStation">
              <label><span class="label">Station code</span><input class="input" v-model.trim="stationForm.station_code" required placeholder="RKAS" /></label>
              <label><span class="label">Station name</span><input class="input" v-model.trim="stationForm.station_name" required placeholder="Rajiv Chowk" /></label>
              <label><span class="label">Line</span><select class="input" v-model.number="stationForm.line_id" required><option disabled value="">Select line</option><option v-for="l in activeLines" :key="l.id" :value="l.id">{{ l.line_code }} — {{ l.line_name }}</option></select></label>
              <label><span class="label">Latitude</span><input class="input" v-model.number="stationForm.latitude" type="number" step="0.000001" placeholder="28.6328" /></label>
              <label><span class="label">Longitude</span><input class="input" v-model.number="stationForm.longitude" type="number" step="0.000001" placeholder="77.2197" /></label>
              <div class="form-actions"><button class="btn btn-primary" type="submit">{{ stationForm.id ? 'Update station' : 'Add station' }}</button><button class="btn btn-muted" type="button" @click="resetStation">Clear</button></div>
            </form>

            <form v-else-if="activeTab === 'contractors'" class="form-grid" @submit.prevent="saveContractor">
              <label><span class="label">Contractor code</span><input class="input" v-model.trim="contractorForm.contractor_code" required placeholder="CTR001" /></label>
              <label><span class="label">Contractor name</span><input class="input" v-model.trim="contractorForm.contractor_name" required placeholder="ABC Housekeeping Pvt Ltd" /></label>
              <label><span class="label">Contact person</span><input class="input" v-model.trim="contractorForm.contact_person" placeholder="Optional" /></label>
              <label><span class="label">Mobile</span><input class="input" v-model.trim="contractorForm.mobile" placeholder="Optional" /></label>
              <label><span class="label">Email</span><input class="input" v-model.trim="contractorForm.email" type="email" placeholder="Optional" /></label>
              <div class="form-actions"><button class="btn btn-primary" type="submit">{{ contractorForm.id ? 'Update contractor' : 'Add contractor' }}</button><button class="btn btn-muted" type="button" @click="resetContractor">Clear</button></div>
            </form>

            <template v-else-if="activeTab === 'contracts'">
              <form class="form-grid contract-form" @submit.prevent="saveContract">
                <label><span class="label">Contract code</span><input class="input" v-model.trim="contractForm.contract_code" required placeholder="DMRC/CHK-Ops-01/2026" /></label>
                <label><span class="label">Tender no</span><input class="input" v-model.trim="contractForm.tender_no" placeholder="Optional" /></label>
                <label class="wide"><span class="label">Contract name</span><input class="input" v-model.trim="contractForm.contract_name" required placeholder="Housekeeping contract name" /></label>
                <label><span class="label">Contractor</span><select class="input" v-model.number="contractForm.contractor_id" required><option disabled value="">Select contractor</option><option v-for="c in activeContractors" :key="c.id" :value="c.id">{{ c.contractor_name }}</option></select></label>
                <label><span class="label">Start date</span><input class="input" v-model="contractForm.start_date" required type="date" /></label>
                <label><span class="label">End date</span><input class="input" v-model="contractForm.end_date" required type="date" /></label>
                <label><span class="label">Extension end date</span><input class="input" v-model="contractForm.extension_end_date" type="date" /></label>
                <label><span class="label">Default monthly bill</span><input class="input" v-model.number="contractForm.monthly_bill_value_default" type="number" step="0.01" min="0" /></label>
                <label><span class="label">Grading scheme</span><select class="input" v-model.number="contractForm.grading_scheme_id" required><option disabled value="">Select scheme</option><option v-for="g in activeGradingSchemes" :key="g.id" :value="g.id">{{ g.name }}</option></select></label>
                <label><span class="label">KPI-6 threshold %</span><input class="input" v-model.number="contractForm.kpi6_threshold_percent" type="number" step="0.01" min="0" max="100" /></label>
                <label><span class="label">KPI-6 penalty %</span><input class="input" v-model.number="contractForm.kpi6_penalty_percent" type="number" step="0.01" min="0" max="100" /></label>
                <div class="form-actions"><button class="btn btn-primary" type="submit">{{ contractForm.id ? 'Update contract' : 'Add contract' }}</button><button class="btn btn-muted" type="button" @click="resetContract">Clear</button></div>
              </form>

              <div class="mapping-card">
                <div>
                  <p class="section-kicker">Station coverage</p>
                  <h3>Map stations to a contract</h3>
                  <p class="muted small-text">This controls which stations are included in KPI-6 calculation for the selected contract.</p>
                </div>
                <div class="mapping-grid">
                  <label><span class="label">Contract</span><select class="input" v-model.number="mapForm.contract_id"><option disabled value="">Select contract</option><option v-for="c in activeContracts" :key="c.id" :value="c.id">{{ c.contract_code }} — {{ c.contract_name }}</option></select></label>
                  <label><span class="label">Station</span><select class="input" v-model.number="mapForm.station_id"><option disabled value="">Select station</option><option v-for="s in activeStations" :key="s.id" :value="s.id">{{ s.station_code }} — {{ s.station_name }}</option></select></label>
                  <button class="btn btn-primary" type="button" @click="mapStation">Map station</button>
                </div>
                <div v-if="mappedStationsForSelectedContract.length" class="mapped-list">
                  <span v-for="m in mappedStationsForSelectedContract" :key="m.id" class="mapped-pill">
                    {{ m.station_code }} — {{ m.station_name }}
                    <button type="button" @click="unmapStation(m)">Remove</button>
                  </span>
                </div>
              </div>
            </template>

            <form v-else-if="activeTab === 'attributes'" class="form-grid" @submit.prevent="saveAttribute">
              <label><span class="label">Attribute code</span><input class="input" v-model.trim="attributeForm.code" required placeholder="ATTR_PLATFORM_AREA" /></label>
              <label><span class="label">Attribute name</span><input class="input" v-model.trim="attributeForm.name" required placeholder="Passenger Movement Area" /></label>
              <label><span class="label">Sort order</span><input class="input" v-model.number="attributeForm.sort_order" type="number" min="1" /></label>
              <label class="wide"><span class="label">Description</span><textarea class="input" v-model.trim="attributeForm.description" rows="2" placeholder="Optional guidance for inspectors"></textarea></label>
              <div class="form-actions"><button class="btn btn-primary" type="submit">{{ attributeForm.id ? 'Update attribute' : 'Add attribute' }}</button><button class="btn btn-muted" type="button" @click="resetAttribute">Clear</button></div>
            </form>

            <form v-else-if="activeTab === 'subareas'" class="form-grid" @submit.prevent="saveSubArea">
              <label><span class="label">Parent attribute</span><select class="input" v-model.number="subAreaForm.attribute_id" required><option disabled value="">Select attribute</option><option v-for="a in activeAttributes" :key="a.id" :value="a.id">{{ a.name }}</option></select></label>
              <label><span class="label">Sub-area code</span><input class="input" v-model.trim="subAreaForm.code" required placeholder="PLATFORM" /></label>
              <label><span class="label">Sub-area name</span><input class="input" v-model.trim="subAreaForm.name" required placeholder="Platform" /></label>
              <label><span class="label">Min photos</span><input class="input" v-model.number="subAreaForm.photo_min_required" type="number" min="0" max="10" /></label>
              <label><span class="label">Max photos</span><input class="input" v-model.number="subAreaForm.photo_max_allowed" type="number" min="1" max="10" /></label>
              <label><span class="label">Video max seconds</span><input class="input" v-model.number="subAreaForm.video_max_seconds" type="number" min="1" /></label>
              <label><span class="label">Sort order</span><input class="input" v-model.number="subAreaForm.sort_order" type="number" min="1" /></label>
              <label class="switch-row"><input v-model="subAreaForm.video_required" type="checkbox" /> <span>Video required</span></label>
              <label class="switch-row"><input v-model="subAreaForm.allow_na" type="checkbox" /> <span>Allow N/A</span></label>
              <div class="form-actions"><button class="btn btn-primary" type="submit">{{ subAreaForm.id ? 'Update sub-area' : 'Add sub-area' }}</button><button class="btn btn-muted" type="button" @click="resetSubArea">Clear</button></div>
            </form>

            <div v-else-if="activeTab === 'grading'" class="grading-editors">
              <form class="form-grid compact-form" @submit.prevent="saveGradingScheme">
                <label><span class="label">Scheme code</span><input class="input" v-model.trim="gradingSchemeForm.code" required placeholder="KPI6_100_90" /></label>
                <label><span class="label">Scheme name</span><input class="input" v-model.trim="gradingSchemeForm.name" required placeholder="KPI-6 Tender Scale" /></label>
                <div class="form-actions"><button class="btn btn-primary" type="submit">{{ gradingSchemeForm.id ? 'Update scheme' : 'Add scheme' }}</button><button class="btn btn-muted" type="button" @click="resetGradingScheme">Clear</button></div>
              </form>

              <form class="form-grid" @submit.prevent="saveGradingOption">
                <label><span class="label">Scheme</span><select class="input" v-model.number="gradingOptionForm.scheme_id" required><option disabled value="">Select scheme</option><option v-for="g in activeGradingSchemes" :key="g.id" :value="g.id">{{ g.name }}</option></select></label>
                <label><span class="label">Grade code</span><input class="input" v-model.trim="gradingOptionForm.grade_code" required placeholder="A" /></label>
                <label><span class="label">Label</span><input class="input" v-model.trim="gradingOptionForm.label" required placeholder="A - Excellent" /></label>
                <label><span class="label">Percentage</span><input class="input" v-model.number="gradingOptionForm.percentage" required type="number" min="0" max="100" step="0.01" /></label>
                <label><span class="label">Sort order</span><input class="input" v-model.number="gradingOptionForm.sort_order" type="number" min="1" /></label>
                <div class="form-actions"><button class="btn btn-primary" type="submit">{{ gradingOptionForm.id ? 'Update option' : 'Add option' }}</button><button class="btn btn-muted" type="button" @click="resetGradingOption">Clear</button></div>
              </form>
            </div>
          </div>

          <div class="record-card">
            <div class="record-header">
              <div>
                <p class="section-kicker">Records</p>
                <h3>{{ activeSection.recordsTitle }}</h3>
                <p class="muted small-text">{{ recordSummary }}</p>
              </div>
            </div>

            <template v-if="activeTab !== 'grading'">
              <MasterTable
                :rows="filteredRows"
                :columns="activeColumns"
                :can-manage="data.can_manage_master"
                :empty-text="`No ${activeSection.label.toLowerCase()} found.`"
                @edit="editCurrent"
                @deactivate="deactivateCurrent"
                @activate="activateCurrent"
              />
            </template>

            <template v-else>
              <div class="split-tables">
                <div>
                  <div class="sub-table-heading"><h4>Grading schemes</h4><span>{{ filteredGradingSchemes.length }} records</span></div>
                  <MasterTable
                    :rows="filteredGradingSchemes"
                    :columns="gradingSchemeColumns"
                    :can-manage="data.can_manage_master"
                    empty-text="No grading schemes found."
                    @edit="editGradingScheme"
                    @deactivate="id => deactivate('/master/grading-schemes', id)"
                    @activate="id => activate('/master/grading-schemes', id)"
                  />
                </div>
                <div>
                  <div class="sub-table-heading"><h4>Grade options</h4><span>{{ filteredGradingOptions.length }} records</span></div>
                  <MasterTable
                    :rows="filteredGradingOptions"
                    :columns="gradingOptionColumns"
                    :can-manage="data.can_manage_master"
                    empty-text="No grade options found."
                    @edit="editGradingOption"
                    @deactivate="id => deactivate('/master/grading-options', id)"
                  />
                </div>
              </div>
            </template>
          </div>
        </main>
      </section>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, reactive, ref, watch } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const loading = ref(false)
const activeTab = ref('lines')
const searchQuery = ref('')
const recordStatusFilter = ref('ALL')
const message = ref('')
const error = ref('')

const data = reactive({
  can_manage_master: false,
  current_role: '',
  lines: [],
  stations: [],
  contractors: [],
  contracts: [],
  contract_stations: [],
  grading_schemes: [],
  grading_options: [],
  inspection_attributes: [],
  inspection_sub_areas: []
})

const sections = [
  { key: 'lines', icon: 'LN', group: 'Network setup', label: 'Lines', title: 'Metro lines', recordsTitle: 'Line register', desc: 'Line codes and names', help: 'Create the metro lines used by stations and reports.' },
  { key: 'stations', icon: 'ST', group: 'Network setup', label: 'Stations', title: 'Stations', recordsTitle: 'Station register', desc: 'Stations mapped to lines', help: 'Maintain station names, codes, line mapping and optional GPS coordinates.' },
  { key: 'contractors', icon: 'CO', group: 'Contract setup', label: 'Contractors', title: 'Contractor agencies', recordsTitle: 'Contractor register', desc: 'Housekeeping agencies', help: 'Create contractor agencies before creating contracts.' },
  { key: 'contracts', icon: 'CT', group: 'Contract setup', label: 'Contracts', title: 'Contracts and station coverage', recordsTitle: 'Contract register', desc: 'Contracts and mapped stations', help: 'Maintain contract dates, bill value, KPI rules and station coverage for KPI-6.' },
  { key: 'attributes', icon: 'AT', group: 'Inspection setup', label: 'Attributes', title: 'Inspection attributes', recordsTitle: 'Attribute register', desc: 'Main inspection categories', help: 'These are the top-level categories shown on the inspection capture screen.' },
  { key: 'subareas', icon: 'SA', group: 'Inspection setup', label: 'Sub-areas', title: 'Inspection sub-areas', recordsTitle: 'Sub-area register', desc: 'Checklist dropdown items', help: 'Sub-areas appear after an attribute is selected and control photo/video requirements.' },
  { key: 'grading', icon: 'GR', group: 'Scoring setup', label: 'Grading', title: 'Grading schemes and options', recordsTitle: 'Grading register', desc: 'Grade percentages', help: 'Manage scoring schemes and grade options used for KPI calculations.' }
]

const MasterTable = defineComponent({
  props: {
    rows: { type: Array, default: () => [] },
    columns: { type: Array, default: () => [] },
    canManage: { type: Boolean, default: false },
    emptyText: { type: String, default: 'No records found.' }
  },
  emits: ['edit', 'deactivate', 'activate'],
  setup(props, { emit }) {
    return () => h('div', { class: 'table-wrap mobile-cards' }, [
      h('table', { class: 'table master-table' }, [
        h('thead', [h('tr', [
          ...props.columns.map((column) => h('th', { key: column.key || column.label }, column.label)),
          ...(props.canManage ? [h('th', { key: 'actions' }, 'Actions')] : [])
        ])]),
        h('tbody', props.rows.length
          ? props.rows.map((row) => h('tr', { key: row.id || JSON.stringify(row), class: row.is_active === false ? 'inactive' : '' }, [
              ...props.columns.map((column) => h('td', { key: column.key || column.label, 'data-label': column.label }, formatCellValue(column.render ? column.render(row) : row[column.key]))),
              ...(props.canManage ? [h('td', { key: 'actions', 'data-label': 'Actions', class: 'table-actions' }, [
                h('button', { class: 'btn btn-sm btn-outline', type: 'button', onClick: () => emit('edit', row) }, 'Edit'),
                row.is_active === false
                  ? h('button', {
                    class: ['btn', 'btn-sm', 'btn-outline', 'activate-action'],
                    type: 'button',
                    onClick: () => emit('activate', row.id)
                  }, 'Activate')
                  : h('button', {
                    class: ['btn', 'btn-sm', 'btn-outline', 'danger-action'],
                    type: 'button',
                    onClick: () => emit('deactivate', row.id)
                  }, 'Deactivate')
              ])] : [])
            ]))
          : [h('tr', [h('td', { colspan: props.columns.length + (props.canManage ? 1 : 0), class: 'empty-state' }, props.emptyText)])]
        )
      ])
    ])
  }
})

const currentRole = computed(() => data.current_role || auth.user?.role || 'UNKNOWN')
const activeSection = computed(() => sections.find((section) => section.key === activeTab.value) || sections[0])

const activeLines = computed(() => activeOnly(data.lines))
const activeStations = computed(() => activeOnly(data.stations))
const activeContractors = computed(() => activeOnly(data.contractors))
const activeContracts = computed(() => activeOnly(data.contracts))
const activeAttributes = computed(() => activeOnly(data.inspection_attributes))
const activeGradingSchemes = computed(() => activeOnly(data.grading_schemes))

const summaryItems = computed(() => [
  { label: 'Lines', value: activeLines.value.length, foot: `${activeStations.value.length} active stations` },
  { label: 'Contracts', value: activeContracts.value.length, foot: `${activeContractors.value.length} active contractors` },
  { label: 'Checklist items', value: activeAttributes.value.length + activeSubAreas.value.length, foot: `${activeSubAreas.value.length} sub-areas` },
  { label: 'Grading', value: activeGradingSchemes.value.length, foot: `${data.grading_options.length} grade options` }
])

const activeSubAreas = computed(() => activeOnly(data.inspection_sub_areas))

const lineColumns = [
  { key: 'line_code', label: 'Code' },
  { key: 'line_name', label: 'Line name' },
  { key: 'station_count', label: 'Stations' },
  { key: 'is_active', label: 'Status', render: statusText }
]
const stationColumns = [
  { key: 'station_code', label: 'Code' },
  { key: 'station_name', label: 'Station' },
  { key: 'line_name', label: 'Line' },
  { key: 'gps', label: 'GPS' },
  { key: 'is_active', label: 'Status', render: statusText }
]
const contractorColumns = [
  { key: 'contractor_code', label: 'Code' },
  { key: 'contractor_name', label: 'Contractor' },
  { key: 'contact_person', label: 'Contact' },
  { key: 'mobile', label: 'Mobile' },
  { key: 'contract_count', label: 'Contracts' },
  { key: 'is_active', label: 'Status', render: statusText }
]
const contractColumns = [
  { key: 'contract_code', label: 'Code' },
  { key: 'contract_summary', label: 'Contract details' },
  { key: 'contractor_name', label: 'Contractor' },
  { key: 'station_count', label: 'Stations' },
  { key: 'commercial_summary', label: 'Bill and KPI rule' },
  { key: 'is_active', label: 'Status', render: statusText }
]
const attributeColumns = [
  { key: 'code', label: 'Code' },
  { key: 'name', label: 'Attribute' },
  { key: 'sub_area_count', label: 'Sub-areas' },
  { key: 'sort_order', label: 'Sort' },
  { key: 'is_active', label: 'Status', render: statusText }
]
const subAreaColumns = [
  { key: 'attribute_name', label: 'Attribute' },
  { key: 'subarea_summary', label: 'Sub-area details' },
  { key: 'evidence_summary', label: 'Evidence rule' },
  { key: 'is_active', label: 'Status', render: statusText }
]
const gradingSchemeColumns = [
  { key: 'code', label: 'Code' },
  { key: 'name', label: 'Scheme' },
  { key: 'option_count', label: 'Options' },
  { key: 'is_active', label: 'Status', render: statusText }
]
const gradingOptionColumns = [
  { key: 'scheme_name', label: 'Scheme' },
  { key: 'grade_code', label: 'Grade' },
  { key: 'label', label: 'Label' },
  { key: 'percentage_display', label: 'Percentage' },
  { key: 'sort_order', label: 'Sort' }
]

const columnMap = {
  lines: lineColumns,
  stations: stationColumns,
  contractors: contractorColumns,
  contracts: contractColumns,
  attributes: attributeColumns,
  subareas: subAreaColumns
}

const activeColumns = computed(() => columnMap[activeTab.value] || [])

const stationRows = computed(() => data.stations.map((row) => ({
  ...row,
  line_name: lineDisplay(row.line_id),
  gps: row.latitude && row.longitude ? `${Number(row.latitude).toFixed(5)}, ${Number(row.longitude).toFixed(5)}` : 'Not set'
})))

const lineRows = computed(() => data.lines.map((row) => ({
  ...row,
  station_count: data.stations.filter((station) => station.line_id === row.id && station.is_active !== false).length
})))

const contractorRows = computed(() => data.contractors.map((row) => ({
  ...row,
  contract_count: data.contracts.filter((contract) => contract.contractor_id === row.id && contract.is_active !== false).length
})))

const contractRows = computed(() => data.contracts.map((row) => {
  const period = `${formatDate(row.start_date)} to ${formatDate(row.extension_end_date || row.end_date)}`
  const monthlyBill = currency(row.monthly_bill_value_default)
  const kpiRule = `Threshold ${formatNumber(row.kpi6_threshold_percent)}% / penalty ${formatNumber(row.kpi6_penalty_percent)}%`
  return {
    ...row,
    contractor_name: contractorName(row.contractor_id),
    grading_scheme_name: schemeName(row.grading_scheme_id),
    period,
    station_count: contractStationCount(row.id),
    monthly_bill_display: monthlyBill,
    kpi_rule: kpiRule,
    contract_summary: `${row.contract_name || 'Unnamed contract'} · ${period}`,
    commercial_summary: `${monthlyBill} · ${kpiRule}`
  }
}))

const attributeRows = computed(() => data.inspection_attributes.map((row) => ({
  ...row,
  sub_area_count: data.inspection_sub_areas.filter((subArea) => subArea.attribute_id === row.id && subArea.is_active !== false).length
})))

const subAreaRows = computed(() => data.inspection_sub_areas.map((row) => {
  const photoRule = `Photos ${row.photo_min_required || 0} min / ${row.photo_max_allowed || 0} max`
  const videoRule = row.video_required ? `Video required, max ${row.video_max_seconds || 0}s` : 'Video optional'
  const naRule = row.allow_na ? 'N/A allowed' : 'N/A not allowed'
  return {
    ...row,
    attribute_name: attributeName(row.attribute_id),
    photo_rule: photoRule,
    video_rule: videoRule,
    subarea_summary: `${row.code || 'Code not set'} · ${row.name || 'Unnamed sub-area'}`,
    evidence_summary: `${photoRule} · ${videoRule} · ${naRule}`
  }
}))

const gradingSchemeRows = computed(() => data.grading_schemes.map((row) => ({
  ...row,
  option_count: data.grading_options.filter((option) => option.scheme_id === row.id).length
})))

const gradingOptionRows = computed(() => data.grading_options.map((row) => ({
  ...row,
  scheme_name: schemeName(row.scheme_id),
  percentage_display: `${formatNumber(row.percentage)}%`
})))

const activeRows = computed(() => {
  const rows = {
    lines: lineRows.value,
    stations: stationRows.value,
    contractors: contractorRows.value,
    contracts: contractRows.value,
    attributes: attributeRows.value,
    subareas: subAreaRows.value
  }
  return rows[activeTab.value] || []
})

const filteredRows = computed(() => filterRows(activeRows.value, activeColumns.value))
const filteredGradingSchemes = computed(() => filterRows(gradingSchemeRows.value, gradingSchemeColumns))
const filteredGradingOptions = computed(() => filterRows(gradingOptionRows.value, gradingOptionColumns))

const mappedStationsForSelectedContract = computed(() => {
  const contractId = Number(mapForm.contract_id || contractForm.id || 0)
  if (!contractId) return []
  return data.contract_stations
    .filter((mapping) => mapping.contract_id === contractId && mapping.is_active !== false)
    .map((mapping) => ({
      ...mapping,
      station_code: stationCode(mapping.station_id),
      station_name: stationName(mapping.station_id)
    }))
})

const recordSummary = computed(() => {
  if (activeTab.value === 'grading') {
    return `${filteredGradingSchemes.value.length} schemes and ${filteredGradingOptions.value.length} grade options shown.`
  }
  const inactiveCount = activeRows.value.filter((row) => row.is_active === false).length
  return `${filteredRows.value.length} of ${activeRows.value.length} records shown · ${inactiveCount} inactive.`
})

const hasActiveEdit = computed(() => {
  const map = {
    lines: lineForm.id,
    stations: stationForm.id,
    contractors: contractorForm.id,
    contracts: contractForm.id,
    attributes: attributeForm.id,
    subareas: subAreaForm.id,
    grading: gradingSchemeForm.id || gradingOptionForm.id
  }
  return Boolean(map[activeTab.value])
})

const editingLabel = computed(() => hasActiveEdit.value ? 'Edit record' : 'New record')
const editorTitle = computed(() => {
  if (activeTab.value === 'grading') return 'Maintain grading scheme and grade options'
  return `${hasActiveEdit.value ? 'Edit' : 'Add'} ${activeSection.value.label.toLowerCase()}`
})

const lineForm = reactive({ id: null, line_code: '', line_name: '' })
const stationForm = reactive({ id: null, station_code: '', station_name: '', line_id: '', latitude: null, longitude: null })
const contractorForm = reactive({ id: null, contractor_code: '', contractor_name: '', contact_person: '', mobile: '', email: '' })
const contractForm = reactive({ id: null, contract_code: '', tender_no: '', contract_name: '', contractor_id: '', start_date: '', end_date: '', extension_end_date: '', monthly_bill_value_default: 0, grading_scheme_id: '', kpi6_threshold_percent: 90, kpi6_penalty_percent: 5 })
const attributeForm = reactive({ id: null, code: '', name: '', description: '', sort_order: 1 })
const subAreaForm = reactive({ id: null, attribute_id: '', code: '', name: '', photo_min_required: 1, photo_max_allowed: 3, video_required: false, video_max_seconds: 15, allow_na: true, sort_order: 1 })
const gradingSchemeForm = reactive({ id: null, code: '', name: '' })
const gradingOptionForm = reactive({ id: null, scheme_id: '', grade_code: '', label: '', percentage: 100, sort_order: 1 })
const mapForm = reactive({ contract_id: '', station_id: '' })

const lineKeys = ['line_code', 'line_name']
const stationKeys = ['station_code', 'station_name', 'line_id', 'latitude', 'longitude']
const contractorKeys = ['contractor_code', 'contractor_name', 'contact_person', 'mobile', 'email']
const contractKeys = ['contract_code', 'tender_no', 'contract_name', 'contractor_id', 'start_date', 'end_date', 'extension_end_date', 'monthly_bill_value_default', 'grading_scheme_id', 'kpi6_threshold_percent', 'kpi6_penalty_percent']
const attributeKeys = ['code', 'name', 'description', 'sort_order']
const subAreaKeys = ['attribute_id', 'code', 'name', 'photo_min_required', 'photo_max_allowed', 'video_required', 'video_max_seconds', 'allow_na', 'sort_order']
const gradingSchemeKeys = ['code', 'name']
const gradingOptionKeys = ['scheme_id', 'grade_code', 'label', 'percentage', 'sort_order']

watch(activeTab, () => {
  searchQuery.value = ''
  clearAlerts()
})

function setTab(key) {
  activeTab.value = key
}

function activeOnly(list) {
  return list.filter((row) => row.is_active !== false)
}

function applyStatusFilter(rows) {
  if (recordStatusFilter.value === 'ACTIVE') return rows.filter((row) => row.is_active !== false)
  if (recordStatusFilter.value === 'INACTIVE') return rows.filter((row) => row.is_active === false)
  return rows
}

function countFor(key) {
  const counts = {
    lines: activeLines.value.length,
    stations: activeStations.value.length,
    contractors: activeContractors.value.length,
    contracts: activeContracts.value.length,
    attributes: activeAttributes.value.length,
    subareas: activeSubAreas.value.length,
    grading: activeGradingSchemes.value.length
  }
  return counts[key] ?? 0
}

function formatCellValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

function filterRows(rows, columns) {
  rows = applyStatusFilter(rows)
  const q = searchQuery.value.toLowerCase()
  if (!q) return rows
  return rows.filter((row) => columns.some((column) => {
    const value = column.render ? column.render(row) : row[column.key]
    return String(formatCellValue(value)).toLowerCase().includes(q)
  }))
}

function statusText(rowOrValue) {
  if (typeof rowOrValue === 'object') return rowOrValue.is_active === false ? 'Inactive' : 'Active'
  return rowOrValue === false ? 'Inactive' : 'Active'
}

function yesNo(value) {
  return value ? 'Yes' : 'No'
}

function formatNumber(value) {
  return Number(value || 0).toFixed(Number(value || 0) % 1 ? 2 : 0)
}

function formatDate(value) {
  if (!value) return 'Not set'
  return new Date(value).toLocaleDateString('en-IN')
}

function currency(value) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0)
}

function lineDisplay(id) {
  const line = data.lines.find((row) => row.id === id)
  return line ? `${line.line_code} — ${line.line_name}` : id
}

function contractorName(id) {
  return data.contractors.find((row) => row.id === id)?.contractor_name || id
}

function schemeName(id) {
  return data.grading_schemes.find((row) => row.id === id)?.name || id
}

function attributeName(id) {
  return data.inspection_attributes.find((row) => row.id === id)?.name || id
}

function stationName(id) {
  return data.stations.find((row) => row.id === id)?.station_name || id
}

function stationCode(id) {
  return data.stations.find((row) => row.id === id)?.station_code || 'Station'
}

function contractStationCount(contractId) {
  return data.contract_stations.filter((mapping) => mapping.contract_id === contractId && mapping.is_active !== false).length
}

function clearAlerts() {
  message.value = ''
  error.value = ''
}

function ok(text) {
  error.value = ''
  message.value = text
  window.setTimeout(() => { message.value = '' }, 2500)
}

function normalizeError(e) {
  const detail = e?.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      const loc = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body').join('.') : ''
      return `${humanizeField(loc)}${loc ? ': ' : ''}${item.msg || 'Invalid value'}`
    }).join(' ')
  }
  if (detail && typeof detail === 'object') {
    return Object.values(detail).flat().join(' ') || JSON.stringify(detail)
  }
  return detail || e?.message || 'Action failed. Please check the values and try again.'
}

function humanizeField(value) {
  return String(value || '').replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function fail(e) {
  message.value = ''
  error.value = normalizeError(e)
}

function pick(form, keys) {
  return keys.reduce((acc, key) => {
    acc[key] = form[key] === '' ? null : form[key]
    return acc
  }, {})
}

async function load() {
  loading.value = true
  try {
    const { data: payload } = await api.get('/master/bootstrap')
    Object.assign(data, payload)
  } catch (e) {
    fail(e)
  } finally {
    loading.value = false
  }
}

async function save(url, form, keys, reset) {
  clearAlerts()
  try {
    const payload = pick(form, keys)
    if (form.id) await api.put(`${url}/${form.id}`, payload)
    else await api.post(url, payload)
    reset()
    await load()
    ok('Master data saved successfully.')
  } catch (e) {
    fail(e)
  }
}

async function deactivate(url, id) {
  if (!window.confirm('Deactivate this record? Existing inspections will remain linked, but this item will no longer appear as active.')) return
  clearAlerts()
  try {
    await api.delete(`${url}/${id}`)
    await load()
    ok('Record deactivated successfully.')
  } catch (e) {
    fail(e)
  }
}

async function activate(url, id) {
  if (!window.confirm('Activate this record again? It will become selectable wherever active master data is used.')) return
  clearAlerts()
  try {
    await api.put(`${url}/${id}/activate`)
    await load()
    ok('Record activated successfully.')
  } catch (e) {
    fail(e)
  }
}

function clearCurrentForm() {
  const resets = {
    lines: resetLine,
    stations: resetStation,
    contractors: resetContractor,
    contracts: resetContract,
    attributes: resetAttribute,
    subareas: resetSubArea,
    grading: () => { resetGradingScheme(); resetGradingOption() }
  }
  resets[activeTab.value]?.()
}

function editCurrent(row) {
  const editors = {
    lines: editLine,
    stations: editStation,
    contractors: editContractor,
    contracts: editContract,
    attributes: editAttribute,
    subareas: editSubArea
  }
  editors[activeTab.value]?.(row)
}

function deactivateCurrent(id) {
  const urls = {
    lines: '/master/lines',
    stations: '/master/stations',
    contractors: '/master/contractors',
    contracts: '/master/contracts',
    attributes: '/master/inspection-attributes',
    subareas: '/master/inspection-sub-areas'
  }
  deactivate(urls[activeTab.value], id)
}

function activateCurrent(id) {
  const urls = {
    lines: '/master/lines',
    stations: '/master/stations',
    contractors: '/master/contractors',
    contracts: '/master/contracts',
    attributes: '/master/inspection-attributes',
    subareas: '/master/inspection-sub-areas'
  }
  activate(urls[activeTab.value], id)
}

function resetLine() { Object.assign(lineForm, { id: null, line_code: '', line_name: '' }) }
function editLine(row) { Object.assign(lineForm, row); activeTab.value = 'lines'; scrollToEditor() }
function saveLine() { save('/master/lines', lineForm, lineKeys, resetLine) }

function resetStation() { Object.assign(stationForm, { id: null, station_code: '', station_name: '', line_id: '', latitude: null, longitude: null }) }
function editStation(row) { Object.assign(stationForm, row); activeTab.value = 'stations'; scrollToEditor() }
function saveStation() { save('/master/stations', stationForm, stationKeys, resetStation) }

function resetContractor() { Object.assign(contractorForm, { id: null, contractor_code: '', contractor_name: '', contact_person: '', mobile: '', email: '' }) }
function editContractor(row) { Object.assign(contractorForm, row); activeTab.value = 'contractors'; scrollToEditor() }
function saveContractor() { save('/master/contractors', contractorForm, contractorKeys, resetContractor) }

function resetContract() {
  Object.assign(contractForm, { id: null, contract_code: '', tender_no: '', contract_name: '', contractor_id: '', start_date: '', end_date: '', extension_end_date: '', monthly_bill_value_default: 0, grading_scheme_id: '', kpi6_threshold_percent: 90, kpi6_penalty_percent: 5 })
  mapForm.contract_id = ''
}
function editContract(row) { Object.assign(contractForm, row); mapForm.contract_id = row.id; activeTab.value = 'contracts'; scrollToEditor() }
function saveContract() { save('/master/contracts', contractForm, contractKeys, resetContract) }

async function mapStation() {
  clearAlerts()
  if (!mapForm.contract_id || !mapForm.station_id) {
    error.value = 'Select both contract and station before mapping.'
    return
  }
  try {
    await api.post(`/master/contracts/${mapForm.contract_id}/stations`, { station_id: Number(mapForm.station_id) })
    mapForm.station_id = ''
    await load()
    ok('Station mapped to contract successfully.')
  } catch (e) {
    fail(e)
  }
}

async function unmapStation(mapping) {
  if (!window.confirm(`Remove ${mapping.station_name} from this contract?`)) return
  clearAlerts()
  try {
    await api.delete(`/master/contracts/${mapping.contract_id}/stations/${mapping.station_id}`)
    await load()
    ok('Station removed from contract.')
  } catch (e) {
    fail(e)
  }
}

function resetAttribute() { Object.assign(attributeForm, { id: null, code: '', name: '', description: '', sort_order: 1 }) }
function editAttribute(row) { Object.assign(attributeForm, row); activeTab.value = 'attributes'; scrollToEditor() }
function saveAttribute() { save('/master/inspection-attributes', attributeForm, attributeKeys, resetAttribute) }

function resetSubArea() { Object.assign(subAreaForm, { id: null, attribute_id: '', code: '', name: '', photo_min_required: 1, photo_max_allowed: 3, video_required: false, video_max_seconds: 15, allow_na: true, sort_order: 1 }) }
function editSubArea(row) { Object.assign(subAreaForm, row); activeTab.value = 'subareas'; scrollToEditor() }
function saveSubArea() { save('/master/inspection-sub-areas', subAreaForm, subAreaKeys, resetSubArea) }

function resetGradingScheme() { Object.assign(gradingSchemeForm, { id: null, code: '', name: '' }) }
function editGradingScheme(row) { Object.assign(gradingSchemeForm, row); activeTab.value = 'grading'; scrollToEditor() }
function saveGradingScheme() { save('/master/grading-schemes', gradingSchemeForm, gradingSchemeKeys, resetGradingScheme) }

function resetGradingOption() { Object.assign(gradingOptionForm, { id: null, scheme_id: '', grade_code: '', label: '', percentage: 100, sort_order: 1 }) }
function editGradingOption(row) { Object.assign(gradingOptionForm, row); activeTab.value = 'grading'; scrollToEditor() }
function saveGradingOption() { save('/master/grading-options', gradingOptionForm, gradingOptionKeys, resetGradingOption) }

function scrollToEditor() {
  window.requestAnimationFrame(() => {
    document.querySelector('.editor-shell')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

onMounted(load)
</script>

<style scoped>
.master-page {
  display: grid;
  gap: 18px;
}

.master-hero {
  display: grid;
  gap: 20px;
}

.hero-toolbar {
  align-items: flex-start;
}

.section-kicker {
  margin: 0 0 6px;
  color: #0f4ca3;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero-actions,
.content-tools {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.access-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 900;
}

.access-pill.editable {
  background: #dcfce7;
  color: #166534;
}

.access-pill.readonly {
  background: #fef3c7;
  color: #92400e;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  border: 1px solid #dbe3f0;
  border-radius: 20px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.78);
}

.summary-card span,
.summary-card small {
  display: block;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.summary-card strong {
  display: block;
  margin: 6px 0 3px;
  color: #0f172a;
  font-size: 28px;
  font-weight: 950;
  letter-spacing: -0.04em;
}

.notice-card {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  border-radius: 18px;
  box-shadow: none;
}

.notice-card strong {
  white-space: nowrap;
}

.warning-card {
  border-color: #fed7aa;
  background: #fff7ed;
  color: #9a3412;
}

.success-card {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #166534;
}

.error-card {
  border-color: #fecaca;
  background: #fef2f2;
  color: #991b1b;
}

.master-workbench {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.master-nav {
  display: grid;
  gap: 10px;
  position: sticky;
  top: 12px;
}

.nav-heading {
  border: 1px solid #dbe3f0;
  border-radius: 20px;
  padding: 14px;
  background: #f8fbff;
}

.nav-heading h2 {
  margin-bottom: 4px;
}

.nav-heading p,
.small-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
}

.nav-item {
  width: 100%;
  border: 1px solid #dbe3f0;
  border-radius: 18px;
  padding: 12px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  background: white;
  text-align: left;
  color: #172033;
  cursor: pointer;
}

.nav-item.active {
  border-color: #0f4ca3;
  background: linear-gradient(135deg, #f8fbff, #eaf1ff);
  box-shadow: 0 14px 28px rgba(15, 76, 163, 0.10);
}

.nav-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #eaf1ff;
  color: #092b6f;
  font-weight: 950;
  font-size: 12px;
}

.nav-copy strong,
.nav-copy small {
  display: block;
}

.nav-copy strong {
  margin-bottom: 2px;
  color: #0f172a;
}

.nav-copy small {
  color: #64748b;
  line-height: 1.35;
}

.nav-count {
  min-width: 30px;
  padding: 5px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 12px;
  font-weight: 900;
  text-align: center;
}

.master-content {
  min-width: 0;
  display: grid;
  gap: 16px;
}

.content-header,
.editor-shell,
.record-card {
  border: 1px solid #dbe3f0;
  border-radius: 22px;
  background: #ffffff;
  padding: 16px;
}

.record-card {
  min-width: 0;
  overflow: hidden;
}


.content-header {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.content-tools .input {
  min-width: 260px;
}

.editor-shell {
  background: linear-gradient(135deg, #fbfdff, #ffffff);
}

.editor-title,
.record-header,
.sub-table-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.editor-title h3,
.record-header h3,
.sub-table-heading h4 {
  margin: 0;
}

.edit-mode-pill,
.sub-table-heading span {
  border-radius: 999px;
  padding: 7px 10px;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  font-weight: 900;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.compact-form {
  grid-template-columns: repeat(2, minmax(0, 1fr)) auto;
}

.form-grid label {
  min-width: 0;
}

.form-grid .wide {
  grid-column: span 2;
}

.form-actions {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.switch-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid #dbe3f0;
  border-radius: 14px;
  background: white;
  font-weight: 800;
  color: #334155;
}

.switch-row input {
  width: auto;
}

.grading-editors {
  display: grid;
  gap: 14px;
}

.mapping-card {
  display: grid;
  gap: 12px;
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #dbeafe;
  border-radius: 20px;
  background: #f8fbff;
}

.mapping-card h3 {
  margin: 0 0 4px;
}

.mapping-grid {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 10px;
  align-items: end;
}

.mapped-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.mapped-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #bfdbfe;
  background: white;
  color: #1e3a8a;
  border-radius: 999px;
  padding: 7px 8px 7px 11px;
  font-size: 12px;
  font-weight: 900;
}

.mapped-pill button {
  border: 0;
  border-radius: 999px;
  background: #fee2e2;
  color: #991b1b;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 900;
}

.table-wrap {
  overflow-x: auto !important;
  overflow-y: visible;
  max-width: 100%;
  -webkit-overflow-scrolling: touch;
}

.master-table {
  min-width: 760px;
  table-layout: fixed;
}

.master-table th,
.master-table td {
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: normal;
  line-height: 1.45;
}

.master-table th:first-child,
.master-table td:first-child {
  width: 112px;
}

.master-table th:last-child,
.master-table td:last-child {
  width: 150px;
}

.master-table tr.inactive td {
  color: #94a3b8;
  background: #f8fafc;
}

.table-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.activate-action {
  color: #166534;
  border-color: #86efac;
  background: #f0fdf4;
}

.danger-action {
  color: #991b1b;
  border-color: #fecaca;
}

.danger-action:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  color: #64748b;
  padding: 28px !important;
}

.split-tables {
  display: grid;
  gap: 18px;
}

@media (max-width: 1180px) {
  .master-workbench {
    grid-template-columns: 1fr;
  }

  .master-nav {
    position: static;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .nav-heading {
    grid-column: 1 / -1;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .content-header,
  .editor-title,
  .record-header {
    display: grid;
  }

  .content-tools {
    justify-content: stretch;
  }

  .content-tools .input {
    min-width: 0;
  }

  .form-grid,
  .compact-form,
  .mapping-grid {
    grid-template-columns: 1fr;
  }

  .form-grid .wide {
    grid-column: auto;
  }
}

@media (max-width: 700px) {
  .master-nav,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .hero-actions,
  .content-tools,
  .notice-card {
    align-items: stretch;
    flex-direction: column;
  }

  .notice-card strong {
    white-space: normal;
  }

  .nav-item {
    grid-template-columns: 38px minmax(0, 1fr) auto;
  }

  .nav-icon {
    width: 38px;
    height: 38px;
  }

  .master-table {
    min-width: 0;
    table-layout: auto;
  }

  .table-actions {
    justify-content: flex-end;
  }
}
</style>
