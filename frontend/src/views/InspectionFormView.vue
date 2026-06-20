<template>
  <AppLayout>
    <section class="hero-panel card entry-hero">
      <div>
        <h1>Inspection Entry Capture</h1>
        <p class="hero-subtitle">Select only the area being inspected. Each saved entry belongs to the same inspection number, with its own attribute, sub-area, grade, evidence and capture metadata.</p>
      </div>
      <div v-if="inspection" class="inspection-badges">
        <span class="badge blue">{{ inspection.inspection_no }}</span>
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

    <div v-else class="inspection-entry-layout section-gap">
      <div class="card capture-card">
        <div class="card-title">
          <div>
            <h2>Add Selected Area Entry</h2>
            <p class="muted">Photo evidence is mandatory as per selected sub-area master data. Save Entry is unlocked only after the required photos are captured/selected.</p>
          </div>
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
        <p class="muted">You can submit with partial selected entries. Each saved entry must satisfy the mandatory photo count from master data.</p>
      </div>
      <div class="submit-actions">
        <button class="btn btn-muted" @click="loadEntries">Refresh Entries</button>
        <button class="btn btn-primary" @click="submitInspection" :disabled="submitting || !entries.length || !canEdit">
          {{ submitting ? 'Submitting...' : 'Submit Inspection' }}
        </button>
      </div>
      <p v-if="message" class="success-text">{{ message }}</p>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
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

const canEdit = computed(() => ['DRAFT', 'RETURNED_FOR_CLARIFICATION'].includes(inspection.value?.status))
const statusClass = computed(() => inspection.value?.status === 'DRAFT' ? 'amber' : 'green')
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

function nowIso(){ return new Date().toISOString() }
function reloadPage(){ window.location.reload() }

function getPhotoFiles(){
  if (Array.isArray(media.value?.photos)) return media.value.photos
  return media.value?.photo ? [media.value.photo] : []
}

function getSubAreaById(id){
  return subAreas.value.find(s => Number(s.id) === Number(id)) || null
}

function onSubAreaChange(subArea){
  selectedSubArea.value = subArea
  clearMedia()
}

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

async function saveEntry(form){
  error.value = ''; message.value = ''
  if (!canEdit.value) { error.value = 'This inspection is already submitted/locked'; return }

  const subArea = getSubAreaById(form.sub_area_id)
  const minRequired = Math.max(1, Number(subArea?.photo_min_required || 1))
  const maxAllowed = Math.max(minRequired, Number(subArea?.photo_max_allowed || 3))
  const photos = getPhotoFiles()
  const hadVideo = !!media.value.video

  if (!subArea) { error.value = 'Please select a valid sub-area before saving'; return }
  if (photos.length < minRequired) { error.value = `This sub-area requires ${minRequired} photo${minRequired === 1 ? '' : 's'}. Selected: ${photos.length}`; return }
  if (photos.length > maxAllowed) { error.value = `Maximum ${maxAllowed} photo${maxAllowed === 1 ? '' : 's'} allowed for this sub-area`; return }
  if (!metadata.captured_at) captureGps()

  saving.value = true
  let uploadFailed = false

  try {
    const payload = {
      attribute_id: form.attribute_id,
      sub_area_id: form.sub_area_id,
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
    message.value = `${entry.entry_no} saved with ${photos.length} photo${photos.length === 1 ? '' : 's'}${hadVideo ? ' and video' : ''}.`
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

async function submitInspection(){
  error.value = ''; message.value = ''
  submitting.value = true
  try {
    const { data } = await api.post(`/inspections/${route.params.id}/submit`, { remarks: inspection.value?.remarks || null })
    inspection.value = data
    message.value = 'Inspection submitted for review.'
  } catch(e) { error.value = apiErrorText(e, 'Unable to submit inspection') }
  finally { submitting.value = false }
}

onMounted(async()=>{
  loading.value = true
  loadError.value = ''
  try {
    inspection.value = (await api.get(`/inspections/${route.params.id}`)).data
    const contractId = route.query.contract_id || inspection.value.contract_id
    const stationId = route.query.station_id || inspection.value.station_id
    const check = (await api.get(`/inspections/checklist?contract_id=${contractId}&station_id=${stationId}`)).data
    checklist.value = { attributes: check.attributes || [], grades: check.grades || check.grading_options || [] }
    await loadEntries()
    captureGps()
  } catch (e) {
    loadError.value = e.response?.data?.detail || 'Unable to load inspection form. Please check API logs and station access mapping.'
  } finally {
    loading.value = false
  }
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
@media(max-width:1080px){ .inspection-entry-layout{grid-template-columns:1fr;} .capture-card{position:relative; top:auto;} .entry-hero,.submit-panel{display:grid;} }
.load-error-card { display:grid; gap:10px; max-width:760px; }
.load-error-card h2 { margin:0; }
.load-error-card p { margin:0; }
</style>
