<template>
  <div class="card attribute-card">
    <div class="attribute-header">
      <div>
        <h2>{{ attributeTitle }}</h2>
        <p class="sub-count">
          {{ subAreas.length }} inspection area{{ subAreas.length === 1 ? '' : 's' }}
        </p>
      </div>

      <div class="grade-box">
        <label>Select Grade</label>
        <select v-model="model.score.grade_code">
          <option value="">Select Grade</option>
          <option
            v-for="grade in grades"
            :key="grade.id || grade.grade_code"
            :value="grade.grade_code"
          >
            {{ gradeLabel(grade) }}
          </option>
        </select>
      </div>
    </div>

    <div class="remarks-box">
      <label>Attribute Remarks</label>
      <textarea
        v-model="model.score.remarks"
        placeholder="Enter overall remarks for this attribute"
        rows="2"
      ></textarea>
    </div>

    <div v-if="subAreas.length === 0" class="empty-box">
      No sub-areas mapped with this attribute.
    </div>

    <div v-else class="sub-area-list">
      <div
        v-for="subArea in subAreas"
        :key="subArea.id"
        class="sub-area-row"
      >
        <div class="sub-area-title">
          {{ subAreaTitle(subArea) }}
        </div>

        <div class="applicable-row">
          <label class="check-label">
            <input
              type="checkbox"
              v-model="model.observations[subArea.id].is_applicable"
            >
            Applicable
          </label>
        </div>

        <div
          v-if="!model.observations[subArea.id].is_applicable"
          class="field-block"
        >
          <label>NA Reason</label>
          <input
            v-model="model.observations[subArea.id].na_reason"
            type="text"
            placeholder="Enter reason for Not Applicable"
          >
        </div>

        <div class="field-block">
          <label>Observation</label>
          <textarea
            v-model="model.observations[subArea.id].observation_text"
            placeholder="Enter observation"
            rows="2"
          ></textarea>
        </div>

        <div class="capture-row">
          <label
            class="capture-btn"
            :for="`photo-${attribute.id}-${subArea.id}`"
          >
            Capture Photo
          </label>

          <input
            class="hidden-input"
            :id="`photo-${attribute.id}-${subArea.id}`"
            type="file"
            accept="image/*"
            capture="environment"
            @change="onMediaSelected(subArea, $event)"
          >

          <label
            class="capture-btn"
            :for="`video-${attribute.id}-${subArea.id}`"
          >
            Capture Video
          </label>

          <input
            class="hidden-input"
            :id="`video-${attribute.id}-${subArea.id}`"
            type="file"
            accept="video/*"
            capture="environment"
            @change="onMediaSelected(subArea, $event)"
          >
        </div>

        <p class="media-note">
          Photo/video will be captured from device camera.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  attribute: {
    type: Object,
    required: true
  },
  grades: {
    type: Array,
    default: () => []
  },
  model: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['media-selected'])

const attributeTitle = computed(() => {
  return (
    props.attribute.attribute_name ||
    props.attribute.name ||
    props.attribute.title ||
    `Attribute ${props.attribute.id}`
  )
})

const subAreas = computed(() => {
  return Array.isArray(props.attribute.sub_areas)
    ? props.attribute.sub_areas
    : []
})

function subAreaTitle(subArea) {
  return (
    subArea.sub_area_name ||
    subArea.name ||
    subArea.title ||
    `Sub Area ${subArea.id}`
  )
}

function gradeLabel(grade) {
  return (
    grade.grade_label ||
    grade.label ||
    grade.name ||
    `${grade.grade_code} = ${grade.grade_percentage ?? ''}%`
  )
}

function onMediaSelected(subArea, event) {
  const files = Array.from(event.target.files || [])

  if (files.length === 0) {
    return
  }

  emit('media-selected', {
    attribute: props.attribute,
    subArea,
    files
  })

  // reset input so same camera/file can be selected again
  event.target.value = ''
}
</script>

<style scoped>
.attribute-card {
  display: grid;
  gap: 16px;
}

.attribute-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 12px;
}

.attribute-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.sub-count {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.grade-box {
  display: grid;
  gap: 6px;
  min-width: 220px;
}

.grade-box label,
.remarks-box label,
.field-block label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

select,
textarea,
input[type="text"] {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  background: #fff;
}

.remarks-box {
  display: grid;
  gap: 6px;
}

.sub-area-list {
  display: grid;
  gap: 12px;
}

.sub-area-row {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 14px;
  background: #f9fafb;
  display: grid;
  gap: 10px;
}

.sub-area-title {
  font-weight: 700;
  color: #111827;
  font-size: 15px;
}

.applicable-row {
  display: flex;
  align-items: center;
}

.check-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.field-block {
  display: grid;
  gap: 6px;
}

.capture-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.capture-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #2563eb;
  background: #2563eb;
  color: white;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

.capture-btn:hover {
  background: #1d4ed8;
}

.hidden-input {
  display: none;
}

.media-note {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
}

.empty-box {
  border: 1px dashed #d1d5db;
  border-radius: 10px;
  padding: 12px;
  color: #6b7280;
  background: #f9fafb;
}
</style>