<template>
  <AppLayout>
    <section class="hero-panel card entry-hero">
      <div>
        <h1>{{ isChemicalKpi ? 'Chemical Quantity Inspection' : 'Inspection Entry Capture' }}</h1>
        <p class="hero-subtitle">{{ isChemicalKpi ? 'Inspect station-wise Chemicals & Consumables by comparing required quantity with actual available quantity.' : 'Search attributes/sub-areas by keyword, or add Other sub-area when the inspected location is not listed.' }}</p>
      </div>
      <div v-if="inspection" class="inspection-badges">
        <span class="badge blue">{{ inspection.inspection_no }}</span>
        <span class="badge">{{ kpiLabel }}</span>
        <span class="badge" :class="statusClass">{{ inspection.status }}</span>
      </div>
    </section>

    <div v-if="loading" class="card section-gap">Loading inspection...</div>

    <div v-else-if="loadError" class="card section-gap load-error-card">
      <h2>Inspection could not be loaded</h2>
      <p>{{ loadError }}</p>
      <p class="muted">If this started after access-control mapping, confirm that the logged-in user has station access for this inspection. Admin can map it from Access Control.</p>
      <button class="btn btn-primary" @click="reloadPage">Retry</button>
    </div>

    <div v-else-if="isChemicalKpi" class="inspection-entry-layout section-gap">
      <div class="card capture-card">
        <div class="card-title"><div><h2>Add Chemical Quantity Entry</h2><p class="muted">Attribute: Supply & utilization of Chemicals & Consumables. Select chemical item, enter actual quantity, and save.</p></div></div>
        <div v-if="canEdit" class="navigation-warning-card"><strong>Unsaved work warning</strong><span>Save chemical quantity entry before leaving. Browser back, refresh, close and menu navigation will ask for confirmation.</span></div>
        <form class="chemical-form" @submit.prevent="saveChemicalEntry">
          <label><span class="label">Chemical / Consumable</span><select class="input" v-model.number="chemicalForm.chemical_id" required @change="onChemicalChange"><option disabled value="">Select mapped chemical</option><option v-for="r in chemicalRequirements" :key="r.chemical_id" :value="r.chemical_id">{{ r.chemical_code }} — {{ r.chemical_name }}</option></select></label>
          <div class="chemical-requirement-card"><strong>Required Quantity</strong><span>{{ selectedChemicalRequirement ? `${selectedChemicalRequirement.required_quantity} ${selectedChemicalRequirement.unit || ''}` : 'Select chemical first' }}</span></div>
          <label><span class="label">Actual Quantity Available</span><input class="input" v-model.number="chemicalForm.actual_quantity" required type="number" min="0" step="0.01" /></label>
          <div class="chemical-requirement-card"><strong>Difference</strong><span>{{ chemicalDifferenceText }}</span></div>
          <label class="wide"><span class="label">Remarks</span><textarea class="input" v-model.trim="chemicalForm.remarks" rows="3" placeholder="Remarks about shortage/excess/condition"></textarea></label>
          <EntryMetadataPreview :metadata="metadata" :error="gpsError" @capture-gps="captureGps" />
          <p v-if="error" class="error">{{ error }}</p>
          <div class="form-actions"><button class="btn btn-primary" type="submit" :disabled="saving || !canEdit || !chemicalForm.chemical_id">{{ saving ? 'Saving...' : 'Save Chemical Entry' }}</button><button class="btn btn-muted" type="button" @click="resetChemicalForm">Clear</button></div>
        </form>
      </div>
      <div class="card">
        <div class="card-title"><div><h2>Saved Chemical Entries</h2><p class="muted">Overall score: <strong>{{ chemicalSummary.score_percent }}%</strong>; shortfall: <strong>{{ chemicalSummary.shortfall_total }}</strong></p></div></div>
        <div class="table-wrap"><table class="table"><thead><tr><th>Chemical</th><th>Required</th><th>Actual</th><th>Diff</th><th>Availability</th><th>Remarks</th><th v-if="canEdit">Action</th></tr></thead><tbody><tr v-for="entry in chemicalEntries" :key="entry.id"><td>{{ entry.chemical_code }} — {{ entry.chemical_name }}</td><td>{{ entry.required_quantity }}</td><td>{{ entry.actual_quantity }}</td><td>{{ entry.difference_quantity }}</td><td>{{ entry.availability_percent }}%</td><td>{{ entry.remarks || '-' }}</td><td v-if="canEdit"><button class="btn btn-sm btn-outline" @click="editChemicalEntry(entry)">Edit</button><button class="btn btn-sm btn-outline danger-action" @click="deleteChemicalEntry(entry)">Delete</button></td></tr><tr v-if="!chemicalEntries.length"><td :colspan="canEdit ? 7 : 6" class="muted">No chemical quantity entries saved yet.</td></tr></tbody></table></div>
      </div>
    </div>

    <div v-else class="inspection-entry-layout section-gap">
      <div class="card capture-card">
        <div class="card-title">
          <div>
            <h2>Add Selected Area Entry</h2>
            <p class="muted">Type inside Attribute/Sub-area fields to filter suggestions. Select Other to add a missing sub-area during inspection.</p>
          </div>
        </div>

        <div v-if="canEdit" class="navigation-warning-card">
          <strong>Unsaved work warning</strong>
          <span>Use Submit Inspection or Save Entry before leaving. Browser back, refresh, close and menu navigation will ask for confirmation.</span>
        </div>

        <EntryCaptureForm
          ref="entryFormRef"
          :attributes="checklist.attributes"
          :grades="checklist.grades"
          :sub-areas="subAreas"
          :loading-sub-areas="loadingSubAreas"
          :saving="saving"
          :error="error"
          :can-save="canSaveCurrentEntry"
          :save-blocked-text="saveBlockedText"
          @attribute-change="loadSubAreas"
          @sub-area-change="onSubAreaChange"
          @save="saveEntry"
          @clear="clearMedia"
        >
          <template #media="{ photoMinRequired, photoMaxAllowed }">
            <MediaCapturePanel
              ref="mediaPanelRef"
              :photo-min-required="photoMinRequired"
              :photo-max-allowed="photoMaxAllowed"
              @change="media = $event"
            />
          </template>
          <template #metadata>
            <EntryMetadataPreview :metadata="metadata" :error="gpsError" @capture-gps="captureGps" />
          </template>
        </EntryCaptureForm>
      </div>

      <SavedEntriesList :entries="entries" :can-edit="canEdit" @delete="deleteEntry" />
    </div>

    <div v-if="!loading && !loadError" class="card submit-panel section-gap">
      <div>
        <h2>Submit Inspection</h2>
        <p class="muted">{{ isChemicalKpi ? 'Submit after saving chemical quantity entries. Report will include required quantity, actual quantity, shortfall and remarks.' : 'You can submit with partial selected entries. Each saved entry must satisfy the mandatory photo count from master data.' }}</p>
      </div>
      <div class="submit-actions">
        <button class="btn btn-muted" @click="refreshCurrentEntries">Refresh Entries</button>
        <button class="btn btn-primary" @click="submitInspection" :disabled="submitting || !canSubmitInspection || !canEdit">
          {{ submitting ? 'Submitting...' : 'Submit Inspection' }}
        </button>
      </div>
      <p v-if="message" class="success-text">{{ message }}</p>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'
import EntryCaptureForm from '../components/EntryCaptureForm.vue'
import EntryMetadataPreview from '../components/EntryMetadataPreview.vue'
import MediaCapturePanel from '../components/MediaCapturePanel.vue'
import SavedEntriesList from '../components/SavedEntriesList.vue'
import { api } from '../services/api'

const route = useRoute()
const loading = ref(true)
const loadingSubAreas = ref(false)
const saving = ref(false)
const submitting = ref(false)
const inspection = ref(null)
const checklist = ref({ attributes: [], grades: [] })
const subAreas = ref([])
const entries = ref([])
const media = ref({ photos: [], photo: null, video: null })
const selectedSubArea = ref(null)
const error = ref('')
const loadError = ref('')
const message = ref('')
const gpsError = ref('')
const entryFormRef = ref(null)
const mediaPanelRef = ref(null)
const metadata = reactive({ latitude: null, longitude: null, gps_accuracy: null, captured_at: null })
const chemicalRequirements = ref([])
const chemicalEntries = ref([])
const chemicalSummary = ref({ required_total: 0, actual_total: 0, shortfall_total: 0, score_percent: 0 })
const chemicalForm = reactive({ id: null, chemical_id: '', actual_quantity: 0, remarks: '' })

const LEAVE_WARNING_MESSAGE = 'You are leaving this inspection capture page. Any unsaved selected area, remarks, GPS capture or photo/video selection will be lost. Saved entries already added will remain. Do you want to leave?'

const canEdit = computed(() => ['DRAFT', 'RETURNED_FOR_CLARIFICATION'].includes(inspection.value?.status))
const statusClass = computed(() => ['DRAFT', 'RETURNED_FOR_CLARIFICATION'].includes(inspection.value?.status) ? 'amber' : 'green')
const selectedPhotoFiles = computed(() => getPhotoFiles())
const requiredPhotoCount = computed(() => Math.max(1, Number(selectedSubArea.value?.photo_min_required || 1)))
const maxPhotoCount = computed(() => Math.max(requiredPhotoCount.value, Number(selectedSubArea.value?.photo_max_allowed || 3)))
const canSaveCurrentEntry = computed(() => canEdit.value && !!selectedSubArea.value && selectedPhotoFiles.value.length >= requiredPhotoCount.value && !saving.value)
const saveBlockedText = computed(() => {
  if (!canEdit.value) return 'Inspection is locked'
  if (!selectedSubArea.value) return 'Select sub-area first'
  const current = selectedPhotoFiles.value.length
  return `Capture mandatory photos first (${current}/${requiredPhotoCount.value})`
})
const isChemicalKpi = computed(() => inspection.value?.kpi_category === 'KPI_CHEMICALS')
const kpiLabel = computed(() => isChemicalKpi.value ? 'KPI Chemicals & Consumables' : 'KPI-6 Cleanliness')
const selectedChemicalRequirement = computed(() => chemicalRequirements.value.find((r) => Number(r.chemical_id) === Number(chemicalForm.chemical_id)) || null)
const chemicalDifferenceText = computed(() => {
  const req = Number(selectedChemicalRequirement.value?.required_quantity || 0)
  const actual = Number(chemicalForm.actual_quantity || 0)
  const diff = actual - req
  if (!selectedChemicalRequirement.value) return 'Select chemical first'
  if (diff < 0) return `Shortfall ${Math.abs(diff).toFixed(2)} ${selectedChemicalRequirement.value.unit || ''}`
  if (diff > 0) return `Excess ${diff.toFixed(2)} ${selectedChemicalRequirement.value.unit || ''}`
  return 'No difference'
})
const canSubmitInspection = computed(() => isChemicalKpi.value ? chemicalEntries.value.length > 0 : entries.value.length > 0)

const shouldWarnBeforeLeaving = computed(() => {
  if (loading.value || loadError.value || !inspection.value) return false
  return Boolean(canEdit.value)
})

function nowIso(){ return new Date().toISOString() }
function reloadPage(){ window.location.reload() }

function getPhotoFiles(){
  if (Array.isArray(media.value?.photos)) return media.value.photos
  return media.value?.photo ? [media.value.photo] : []
}

function getSubAreaById(id){
  if (!id) return null
  return subAreas.value.find(s => Number(s.id) === Number(id)) || null
}

function onSubAreaChange(subArea){
  selectedSubArea.value = subArea
  clearMedia()
}

function confirmLeaveInspectionPage(){
  if (!shouldWarnBeforeLeaving.value) return true
  if (typeof window === 'undefined') return true
  return window.confirm(LEAVE_WARNING_MESSAGE)
}

function beforeUnloadHandler(event){
  if (!shouldWarnBeforeLeaving.value) return
  event.preventDefault()
  event.returnValue = LEAVE_WARNING_MESSAGE
  return LEAVE_WARNING_MESSAGE
}

onBeforeRouteLeave(() => confirmLeaveInspectionPage())

function captureGps(){
  gpsError.value = ''
  metadata.captured_at = nowIso()
  if (!navigator.geolocation) { gpsError.value = 'Geolocation is not supported by this browser'; return }
  navigator.geolocation.getCurrentPosition(pos => {
    metadata.latitude = pos.coords.latitude
    metadata.longitude = pos.coords.longitude
    metadata.gps_accuracy = pos.coords.accuracy
    metadata.captured_at = nowIso()
  }, () => { gpsError.value = 'GPS permission denied or unavailable'; metadata.captured_at = nowIso() }, { enableHighAccuracy: true, timeout: 10000 })
}

async function loadSubAreas(attributeId){
  subAreas.value = []
  selectedSubArea.value = null
  clearMedia()
  if (!attributeId) return
  loadingSubAreas.value = true
  try { subAreas.value = (await api.get(`/master/inspection-attributes/${attributeId}/sub-areas`)).data }
  finally { loadingSubAreas.value = false }
}

async function loadEntries(){
  entries.value = (await api.get(`/inspections/${route.params.id}/entries`)).data
}

function appendOptionalFormValue(fd, key, value){
  // Do not send empty strings for optional numeric/date fields.
  // FastAPI can reject blank multipart fields before the endpoint runs.
  if (value === null || value === undefined || value === '') return
  fd.append(key, String(value))
}

function apiErrorText(e, fallback = 'Request failed'){
  const detail = e?.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail.map(item => {
      const location = Array.isArray(item.loc) ? item.loc.join('.') : ''
      return `${location ? location + ': ' : ''}${item.msg || JSON.stringify(item)}`
    }).join('; ')
  }
  if (typeof detail === 'string') return detail
  if (detail) return JSON.stringify(detail)
  if (e?.message) return e.message
  return fallback
}

async function uploadFile(entryId, file, mediaType){
  const fd = new FormData()
  fd.append('media_type', mediaType)
  appendOptionalFormValue(fd, 'captured_latitude', metadata.latitude)
  appendOptionalFormValue(fd, 'captured_longitude', metadata.longitude)
  appendOptionalFormValue(fd, 'gps_accuracy', metadata.gps_accuracy)
  appendOptionalFormValue(fd, 'captured_at', metadata.captured_at || nowIso())
  fd.append('file', file, file.name || `${mediaType.toLowerCase()}-${Date.now()}`)

  // Let the browser/axios set the multipart boundary automatically.
  await api.post(`/inspections/${route.params.id}/entries/${entryId}/media`, fd)
}

function resolveSelectedSubAreaForSave(form){
  const customName = String(form.custom_sub_area_name || '').trim()
  if (customName) {
    return {
      id: null,
      name: customName,
      photo_min_required: 1,
      photo_max_allowed: 3,
      is_custom: true,
    }
  }
  return getSubAreaById(form.sub_area_id)
}

async function saveEntry(form){
  error.value = ''; message.value = ''
  if (!canEdit.value) { error.value = 'This inspection is already submitted/locked'; return }

  const customSubAreaName = String(form.custom_sub_area_name || '').trim()
  const subArea = resolveSelectedSubAreaForSave(form)
  const minRequired = Math.max(1, Number(subArea?.photo_min_required || 1))
  const maxAllowed = Math.max(minRequired, Number(subArea?.photo_max_allowed || 3))
  const photos = getPhotoFiles()
  const hadVideo = !!media.value.video

  if (!subArea) { error.value = 'Please select a valid sub-area or choose Other before saving'; return }
  if (customSubAreaName && customSubAreaName.length < 2) { error.value = 'Other sub-area name must be at least 2 characters'; return }
  if (photos.length < minRequired) { error.value = `This sub-area requires ${minRequired} photo${minRequired === 1 ? '' : 's'}. Selected: ${photos.length}`; return }
  if (photos.length > maxAllowed) { error.value = `Maximum ${maxAllowed} photo${maxAllowed === 1 ? '' : 's'} allowed for this sub-area`; return }
  if (!metadata.captured_at) captureGps()

  saving.value = true
  let uploadFailed = false

  try {
    const payload = {
      attribute_id: form.attribute_id,
      sub_area_id: customSubAreaName ? null : form.sub_area_id,
      custom_sub_area_name: customSubAreaName || null,
      grade_code: form.grade_code,
      remarks: form.remarks,
      captured_latitude: metadata.latitude,
      captured_longitude: metadata.longitude,
      gps_accuracy: metadata.gps_accuracy,
      captured_at: metadata.captured_at || nowIso(),
    }

    const { data: entry } = await api.post(`/inspections/${route.params.id}/entries`, payload)

    try {
      for (let index = 0; index < photos.length; index += 1) {
        try {
          await uploadFile(entry.id, photos[index], 'PHOTO')
        } catch (photoUploadError) {
          photoUploadError.uploadLabel = `Photo ${index + 1}`
          throw photoUploadError
        }
      }
      if (media.value.video) {
        try {
          await uploadFile(entry.id, media.value.video, 'VIDEO')
        } catch (videoUploadError) {
          videoUploadError.uploadLabel = 'Video'
          throw videoUploadError
        }
      }
    } catch (uploadError) {
      uploadFailed = true
      // Avoid orphan entries without complete mandatory photo evidence.
      try { await api.delete(`/inspections/${route.params.id}/entries/${entry.id}`) } catch (_) {}
      throw uploadError
    }

    await loadEntries()
    clearMedia()
    entryFormRef.value?.resetForm()
    message.value = `${entry.entry_no} saved for ${entry.sub_area_name || subArea.name} with ${photos.length} photo${photos.length === 1 ? '' : 's'}${hadVideo ? ' and video' : ''}.`
  } catch (e) {
    const reason = `${e.uploadLabel ? e.uploadLabel + ': ' : ''}${apiErrorText(e, 'Unable to save entry')}`
    error.value = uploadFailed
      ? `Evidence upload failed, so the entry was not saved. Reason: ${reason}`
      : reason
  } finally {
    saving.value = false
  }
}

function clearMedia(){
  media.value = { photos: [], photo: null, video: null }
  mediaPanelRef.value?.reset()
}

async function deleteEntry(entry){
  if (!confirm(`Delete ${entry.entry_no}?`)) return
  await api.delete(`/inspections/${route.params.id}/entries/${entry.id}`)
  await loadEntries()
}


async function loadChemicalEntries(){
  const { data } = await api.get(`/kpi-chemicals/inspections/${route.params.id}/entries`)
  chemicalEntries.value = data.items || []
  chemicalSummary.value = data.summary || { required_total: 0, actual_total: 0, shortfall_total: 0, score_percent: 0 }
}

async function loadChemicalRequirements(){
  chemicalRequirements.value = (await api.get(`/kpi-chemicals/inspections/${route.params.id}/requirements`)).data || []
}

function onChemicalChange(){
  const existing = chemicalEntries.value.find((entry) => Number(entry.chemical_id) === Number(chemicalForm.chemical_id))
  if (existing) editChemicalEntry(existing)
}

function resetChemicalForm(){
  Object.assign(chemicalForm, { id: null, chemical_id: '', actual_quantity: 0, remarks: '' })
}

function editChemicalEntry(entry){
  Object.assign(chemicalForm, { id: entry.id, chemical_id: entry.chemical_id, actual_quantity: entry.actual_quantity, remarks: entry.remarks || '' })
}

async function saveChemicalEntry(){
  error.value = ''; message.value = ''
  if (!canEdit.value) { error.value = 'This inspection is already submitted/locked'; return }
  if (!selectedChemicalRequirement.value) { error.value = 'Select a station-mapped chemical first'; return }
  saving.value = true
  try {
    const payload = {
      chemical_id: Number(chemicalForm.chemical_id),
      actual_quantity: Number(chemicalForm.actual_quantity || 0),
      remarks: chemicalForm.remarks || null,
      captured_latitude: metadata.latitude,
      captured_longitude: metadata.longitude,
      gps_accuracy: metadata.gps_accuracy,
      captured_at: metadata.captured_at || nowIso(),
    }
    const { data } = await api.post(`/kpi-chemicals/inspections/${route.params.id}/entries`, payload)
    await loadChemicalEntries()
    resetChemicalForm()
    message.value = `${data.chemical_name || 'Chemical'} quantity saved. Availability ${data.availability_percent}%.`
  } catch(e) { error.value = apiErrorText(e, 'Unable to save chemical entry') }
  finally { saving.value = false }
}

async function deleteChemicalEntry(entry){
  if (!confirm(`Delete chemical entry for ${entry.chemical_name}?`)) return
  await api.delete(`/kpi-chemicals/inspections/${route.params.id}/entries/${entry.id}`)
  await loadChemicalEntries()
}

async function refreshCurrentEntries(){
  if (isChemicalKpi.value) await loadChemicalEntries()
  else await loadEntries()
}

async function submitInspection(){
  error.value = ''; message.value = ''
  submitting.value = true
  try {
    const submitUrl = isChemicalKpi.value ? `/kpi-chemicals/inspections/${route.params.id}/submit` : `/inspections/${route.params.id}/submit`
    const { data } = await api.post(submitUrl, { remarks: inspection.value?.remarks || null })
    inspection.value = data
    message.value = 'Inspection submitted for review.'
  } catch(e) { error.value = apiErrorText(e, 'Unable to submit inspection') }
  finally { submitting.value = false }
}

onMounted(async()=>{
  if (typeof window !== 'undefined') window.addEventListener('beforeunload', beforeUnloadHandler)
  loading.value = true
  loadError.value = ''
  try {
    inspection.value = (await api.get(`/inspections/${route.params.id}`)).data
    const contractId = route.query.contract_id || inspection.value.contract_id
    const stationId = route.query.station_id || inspection.value.station_id
    if (inspection.value.kpi_category === 'KPI_CHEMICALS') {
      await loadChemicalRequirements()
      await loadChemicalEntries()
    } else {
      const check = (await api.get('/inspections/checklist', { params: { contract_id: contractId, station_id: stationId, inspection_id: inspection.value.id } })).data
      checklist.value = { attributes: check.attributes || [], grades: check.grades || check.grading_options || [] }
      await loadEntries()
    }
    captureGps()
  } catch (e) {
    loadError.value = e.response?.data?.detail || 'Unable to load inspection form. Please check API logs and station access mapping.'
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') window.removeEventListener('beforeunload', beforeUnloadHandler)
})
</script>

<style scoped>
.entry-hero { display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }
.inspection-badges { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.inspection-entry-layout { display:grid; grid-template-columns:minmax(360px, 0.85fr) minmax(420px, 1.15fr); gap:18px; align-items:start; }
.capture-card { position:sticky; top:18px; }
.submit-panel { display:flex; justify-content:space-between; gap:14px; align-items:center; }
.submit-actions { display:flex; gap:10px; flex-wrap:wrap; }
.success-text { color:#166534; font-weight:900; margin:0; }
.navigation-warning-card { display:grid; gap:4px; margin:0 0 14px; border:1px solid #fed7aa; border-radius:16px; background:#fff7ed; color:#9a3412; padding:12px 14px; font-size:0.9rem; line-height:1.45; }
.navigation-warning-card strong { color:#7c2d12; }
@media(max-width:1080px){ .inspection-entry-layout{grid-template-columns:1fr;} .capture-card{position:relative; top:auto;} .entry-hero,.submit-panel{display:grid;} }
.load-error-card { display:grid; gap:10px; max-width:760px; }
.load-error-card h2 { margin:0; }
.load-error-card p { margin:0; }
.chemical-form { display:grid; gap:12px; }
.chemical-form .wide { grid-column:1/-1; }
.chemical-requirement-card { display:grid; gap:4px; border:1px solid #dbeafe; border-radius:14px; background:#eff6ff; color:#1e3a8a; padding:12px; }
.form-actions { display:flex; gap:10px; flex-wrap:wrap; }
.danger-action { color:#b91c1c; border-color:#fecaca; }
</style>
