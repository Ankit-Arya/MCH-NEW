<template>
  <AppLayout>
    <h1>Inspection Form</h1>

    <div class="card debug">
      Debug Step: {{ debugStep }}
      <br>
      Loading: {{ loading }}
      <br>
      Error: {{ error || 'No error' }}
      <br>
      Attributes: {{ checklist.attributes.length }}
      <br>
      Sub Areas: {{ checklist.sub_areas.length }}
      <br>
      Grades: {{ checklist.grading_options.length }}
    </div>

    <div v-if="inspection" class="badge">
      {{ inspection.inspection_no }} - {{ inspection.status }}
    </div>

    <div v-if="loading" class="card">
      Loading checklist...
    </div>

    <div v-else-if="error" class="card error">
      {{ error }}
    </div>

    <div v-else class="grid">
      <div v-if="checklist.attributes.length === 0" class="card error">
        No inspection attributes found.
      </div>

      <AttributeCard
        v-for="attr in checklist.attributes"
        :key="attr.id"
        :attribute="attr"
        :grades="checklist.grading_options"
        :model="models[attr.id]"
        @media-selected="uploadMedia"
      />

      <div class="card actions">
        <button class="btn btn-muted" @click="saveDraft" :disabled="saving">
          {{ saving ? 'Saving...' : 'Save Draft' }}
        </button>

        <button class="btn btn-primary" @click="submitInspection" :disabled="submitting">
          {{ submitting ? 'Submitting...' : 'Submit Inspection' }}
        </button>

        <p v-if="message" class="success">
          {{ message }}
        </p>
      </div>

      <details class="card">
        <summary>Raw Checklist JSON</summary>
        <pre>{{ rawChecklist }}</pre>
      </details>
    </div>
  </AppLayout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'
import AttributeCard from '../components/AttributeCard.vue'
import { api } from '../services/api'

const route = useRoute()

const loading = ref(true)
const saving = ref(false)
const submitting = ref(false)

const message = ref('')
const error = ref('')
const debugStep = ref('Component loaded')

const inspection = ref(null)
const rawChecklist = ref(null)

const checklist = ref({
  contract: null,
  station: null,
  grading_options: [],
  attributes: [],
  sub_areas: []
})

const models = ref({})

function normalizeChecklist(data) {
  debugStep.value = 'Normalizing checklist'

  const subAreas = Array.isArray(data?.sub_areas) ? data.sub_areas : []
  const attributes = Array.isArray(data?.attributes) ? data.attributes : []
  const gradingOptions = Array.isArray(data?.grading_options) ? data.grading_options : []

  checklist.value = {
    contract: data?.contract || null,
    station: data?.station || null,
    grading_options: gradingOptions,
    sub_areas: subAreas,
    attributes: attributes.map(attr => ({
      ...attr,
      sub_areas: Array.isArray(attr.sub_areas) ? attr.sub_areas : subAreas
    }))
  }
}

function initModels() {
  debugStep.value = 'Initializing models'

  const nextModels = {}

  for (const attr of checklist.value.attributes) {
    nextModels[attr.id] = {
      score: {
        attribute_id: attr.id,
        grade_code: '',
        remarks: ''
      },
      observations: {}
    }

    const subAreas = Array.isArray(attr.sub_areas) ? attr.sub_areas : []

    for (const s of subAreas) {
      nextModels[attr.id].observations[s.id] = {
        attribute_id: attr.id,
        sub_area_id: s.id,
        is_applicable: true,
        na_reason: '',
        observation_text: ''
      }
    }
  }

  models.value = nextModels
}

function buildPayload() {
  const attribute_scores = []
  const observations = []

  Object.values(models.value).forEach(model => {
    attribute_scores.push(model.score)
    observations.push(...Object.values(model.observations))
  })

  return {
    attribute_scores,
    observations
  }
}

async function saveDraft() {
  saving.value = true
  message.value = ''
  error.value = ''

  try {
    await api.put(`/inspections/${route.params.id}/draft`, buildPayload())
    message.value = 'Draft saved'
  } catch (err) {
    console.error('Draft save failed:', err)
    error.value = err.response?.data?.detail || err.message || 'Draft save failed'
  } finally {
    saving.value = false
  }
}

async function submitInspection() {
  submitting.value = true
  message.value = ''
  error.value = ''

  try {
    const response = await api.post(
      `/inspections/${route.params.id}/submit`,
      buildPayload()
    )

    inspection.value = response.data
    message.value = 'Inspection submitted'
  } catch (err) {
    console.error('Inspection submit failed:', err)
    error.value = err.response?.data?.detail || err.message || 'Inspection submit failed'
  } finally {
    submitting.value = false
  }
}

async function uploadMedia({ attribute, subArea, files }) {
  message.value = ''
  error.value = ''

  try {
    for (const file of files) {
      const fd = new FormData()

      fd.append('attribute_id', attribute.id)
      fd.append('sub_area_id', subArea.id)
      fd.append('media_type', file.type.startsWith('video') ? 'VIDEO' : 'PHOTO')
      fd.append('file', file)

      await api.post(`/inspections/${route.params.id}/media`, fd, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
    }

    message.value = 'Media uploaded'
  } catch (err) {
    console.error('Media upload failed:', err)
    error.value = err.response?.data?.detail || err.message || 'Media upload failed'
  }
}

onMounted(async () => {
  loading.value = true
  error.value = ''
  message.value = ''

  try {
    debugStep.value = 'Loading inspection'

    const inspectionResponse = await api.get(`/inspections/${route.params.id}`)
    inspection.value = inspectionResponse.data

    debugStep.value = 'Inspection loaded'

    const contractId = route.query.contract_id || inspection.value.contract_id
    const stationId = route.query.station_id || inspection.value.station_id

    if (!contractId || !stationId) {
      throw new Error('contract_id or station_id missing')
    }

    debugStep.value = `Loading checklist for contract ${contractId}, station ${stationId}`

    const checklistResponse = await api.get('/inspections/checklist', {
      params: {
        contract_id: contractId,
        station_id: stationId
      }
    })

    debugStep.value = 'Checklist API response received'
    rawChecklist.value = checklistResponse.data

    normalizeChecklist(checklistResponse.data)
    initModels()

    debugStep.value = 'Ready'
  } catch (err) {
    console.error('Checklist loading failed:', err)
    error.value = err.response?.data?.detail || err.message || 'Checklist loading failed'
    debugStep.value = 'Failed'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.grid {
  display: grid;
  gap: 16px;
}

.actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.error {
  color: #b91c1c;
}

.success {
  color: #15803d;
}

.debug {
  background: #f8fafc;
  font-size: 13px;
  line-height: 1.6;
}

pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
</style>