<template>
  <form class="entry-form" @submit.prevent="submitEntry">
    <div class="form-step">
      <div class="step-heading">
        <span class="step-badge">1</span>
        <div>
          <strong>Select inspection area and grade</strong>
          <span>Choose the exact attribute/sub-area before capturing evidence.</span>
        </div>
      </div>

      <div class="grid grid-2">
        <div>
          <label class="label">Attribute</label>
          <select class="input" v-model="form.attribute_id" required @change="onAttributeChange">
            <option value="">Select attribute</option>
            <option v-for="a in attributes" :key="a.id" :value="a.id">{{ a.name }}</option>
          </select>
        </div>
        <div>
          <label class="label">Sub-area</label>
          <select class="input" v-model="form.sub_area_id" required :disabled="!form.attribute_id || loadingSubAreas" @change="onSubAreaChange">
            <option value="">{{ loadingSubAreas ? 'Loading...' : 'Select sub-area' }}</option>
            <option v-for="s in subAreas" :key="s.id" :value="s.id">
              {{ subAreaOptionLabel(s) }}
            </option>
          </select>
        </div>
      </div>

      <div class="grid grid-2">
        <div>
          <label class="label">Grade</label>
          <select class="input" v-model="form.grade_code" required>
            <option value="">Select grade</option>
            <option v-for="g in grades" :key="g.id || g.grade_code" :value="g.grade_code">
              {{ g.grade_code }} - {{ g.label || (g.percentage + '%') }}
            </option>
          </select>
        </div>
      </div>

      <div>
        <label class="label">Remarks</label>
        <textarea class="input" rows="3" v-model="form.remarks" placeholder="Write what was observed at this exact location/sub-area"></textarea>
      </div>
    </div>

    <div class="form-step evidence-step">
      <div class="step-heading">
        <span class="step-badge">2</span>
        <div>
          <strong>Capture evidence</strong>
          <span>{{ evidenceHelpText }}</span>
        </div>
      </div>

      <slot
        name="media"
        :selected-sub-area="selectedSubArea"
        :photo-min-required="photoMinRequired"
        :photo-max-allowed="photoMaxAllowed"
      ></slot>
      <slot name="metadata"></slot>
    </div>

    <div class="entry-actions" :class="{ ready: canSave }">
      <div class="save-status">
        <strong>{{ canSave ? 'Ready to save entry' : saveBlockedText }}</strong>
        <span>
          {{ canSave
            ? 'Mandatory photo evidence is selected. Save will create the entry and upload all selected evidence together.'
            : `Select sub-area and capture/select ${photoMinRequired} mandatory photo${photoMinRequired === 1 ? '' : 's'} first.` }}
        </span>
      </div>
      <div class="button-row">
        <button type="submit" class="btn btn-primary" :disabled="saving || !canSave">
          {{ saving ? 'Saving entry...' : 'Save Entry' }}
        </button>
        <button type="button" class="btn btn-muted" @click="resetForm" :disabled="saving">Clear</button>
      </div>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>
  </form>
</template>

<script setup>
import { computed, reactive } from 'vue'

const props = defineProps({
  attributes: { type: Array, default: () => [] },
  grades: { type: Array, default: () => [] },
  subAreas: { type: Array, default: () => [] },
  loadingSubAreas: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  error: { type: String, default: '' },
  canSave: { type: Boolean, default: false },
  saveBlockedText: { type: String, default: 'Capture mandatory photo first' },
})

const emit = defineEmits(['attribute-change', 'sub-area-change', 'save', 'clear'])
const form = reactive({ attribute_id: '', sub_area_id: '', grade_code: '', remarks: '' })

const selectedSubArea = computed(() => props.subAreas.find(s => Number(s.id) === Number(form.sub_area_id)) || null)
const photoMinRequired = computed(() => Math.max(1, Number(selectedSubArea.value?.photo_min_required || 1)))
const photoMaxAllowed = computed(() => Math.max(photoMinRequired.value, Number(selectedSubArea.value?.photo_max_allowed || 3)))
const evidenceHelpText = computed(() => `Photo evidence is mandatory: ${photoMinRequired.value} required, up to ${photoMaxAllowed.value} allowed. Video remains optional.`)

function subAreaOptionLabel(subArea){
  const required = Number(subArea.photo_min_required || 0)
  if (!required) return subArea.name
  return `${subArea.name} · ${required} photo${required === 1 ? '' : 's'}`
}

function onAttributeChange(){
  form.sub_area_id = ''
  emit('sub-area-change', null)
  emit('attribute-change', Number(form.attribute_id) || null)
}

function onSubAreaChange(){
  emit('sub-area-change', selectedSubArea.value)
}

function submitEntry(){
  if (!props.canSave || props.saving) return
  emit('save', { ...form, attribute_id: Number(form.attribute_id), sub_area_id: Number(form.sub_area_id) })
}

function resetForm(){
  form.attribute_id = ''
  form.sub_area_id = ''
  form.grade_code = ''
  form.remarks = ''
  emit('sub-area-change', null)
  emit('attribute-change', null)
  emit('clear')
}

defineExpose({ resetForm })
</script>

<style scoped>
.entry-form { display:grid; gap:16px; }
.form-step { display:grid; gap:14px; }
.step-heading { display:flex; gap:10px; align-items:flex-start; }
.step-heading strong { display:block; color:#0f172a; font-size:14px; }
.step-heading span:not(.step-badge) { display:block; color:#64748b; font-size:12px; line-height:1.45; margin-top:2px; }
.step-badge { width:28px; height:28px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:#eaf2ff; color:#174ea6; font-weight:900; flex:0 0 28px; }
.evidence-step { border-top:1px solid #e8eef7; padding-top:16px; }
.entry-actions { border:1px solid #e5e7eb; border-radius:18px; padding:14px; display:flex; gap:14px; align-items:center; justify-content:space-between; background:#f8fafc; }
.entry-actions.ready { border-color:#bbf7d0; background:#f0fdf4; }
.save-status { display:grid; gap:3px; min-width:0; }
.save-status strong { color:#0f172a; font-size:14px; }
.save-status span { color:#64748b; font-size:12px; line-height:1.45; }
.button-row { display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end; }
.error-text { color:#b91c1c; font-weight:800; margin:0; }
button:disabled { opacity:.58; cursor:not-allowed; }
@media(max-width:760px){ .entry-actions{display:grid;} .button-row{justify-content:stretch;} .button-row .btn{width:100%;} }
</style>
