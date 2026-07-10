<template>
  <form class="entry-form" @submit.prevent="submitEntry">
    <div class="form-step">
      <div class="step-heading">
        <span class="step-badge">1</span>
        <div>
          <strong>Select inspection area and grade</strong>
          <span>Search by typing attribute or sub-area keywords. Use Other when the sub-area is not available in master data.</span>
        </div>
      </div>

      <div class="grid grid-2">
        <div class="search-field">
          <label class="label">Attribute</label>
          <div class="searchable-select" :class="{ open: attributeOpen }">
            <input
              class="input"
              v-model.trim="attributeSearch"
              type="text"
              autocomplete="off"
              placeholder="Type attribute keyword"
              required
              @focus="attributeOpen = true"
              @input="onAttributeSearchInput"
              @blur="closeAttributeMenuSoon"
            />
            <div v-if="attributeOpen" class="option-panel">
              <button
                v-for="a in filteredAttributes"
                :key="a.id"
                type="button"
                class="option-row"
                @mousedown.prevent="selectAttribute(a)"
              >
                <strong>{{ a.name }}</strong>
                <small v-if="a.code || a.description">{{ [a.code, a.description].filter(Boolean).join(' · ') }}</small>
              </button>
              <div v-if="!filteredAttributes.length" class="option-empty">No matching attribute found.</div>
            </div>
          </div>
          <p v-if="form.attribute_id" class="field-hint">Selected: {{ selectedAttribute?.name }}</p>
        </div>

        <div class="search-field">
          <label class="label">Sub-area</label>
          <div class="searchable-select" :class="{ open: subAreaOpen, disabled: !form.attribute_id || loadingSubAreas }">
            <input
              class="input"
              v-model.trim="subAreaSearch"
              type="text"
              autocomplete="off"
              :disabled="!form.attribute_id || loadingSubAreas"
              :placeholder="subAreaPlaceholder"
              required
              @focus="subAreaOpen = true"
              @input="onSubAreaSearchInput"
              @blur="closeSubAreaMenuSoon"
            />
            <div v-if="subAreaOpen && form.attribute_id && !loadingSubAreas" class="option-panel">
              <button
                v-for="s in filteredSubAreas"
                :key="s.id"
                type="button"
                class="option-row"
                @mousedown.prevent="selectSubArea(s)"
              >
                <strong>{{ s.name }}</strong>
                <small>{{ subAreaOptionMeta(s) }}</small>
              </button>
              <button
                type="button"
                class="option-row other-option"
                @mousedown.prevent="selectOtherSubArea"
              >
                <strong>{{ otherOptionLabel }}</strong>
                <small>Use this when the inspected sub-area is not listed.</small>
              </button>
            </div>
          </div>
          <p v-if="form.sub_area_id && form.sub_area_id !== OTHER_SUB_AREA_VALUE" class="field-hint">Selected: {{ selectedSubArea?.name }}</p>
        </div>
      </div>

      <div v-if="isOtherSubArea" class="other-sub-area-box">
        <label class="label">Other sub-area name</label>
        <input
          class="input"
          v-model.trim="form.custom_sub_area_name"
          type="text"
          maxlength="250"
          placeholder="Enter new sub-area name, e.g. PF-1 lift lobby wall"
          required
          @input="onCustomSubAreaInput"
        />
        <p class="field-hint">
          This name will be saved under the selected attribute and can be reused in future inspections.
          Default evidence rule for Other is 1 mandatory photo and up to 3 photos.
        </p>
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

    <div class="entry-actions" :class="{ ready: canSubmitForm }">
      <div class="save-status">
        <strong>{{ canSubmitForm ? 'Ready to save entry' : localSaveBlockedText }}</strong>
        <span>
          {{ canSubmitForm
            ? 'Mandatory photo evidence is selected. Save will create the entry and upload all selected evidence together.'
            : `Select attribute/sub-area and capture/select ${photoMinRequired} mandatory photo${photoMinRequired === 1 ? '' : 's'} first.` }}
        </span>
      </div>
      <div class="button-row">
        <button type="submit" class="btn btn-primary" :disabled="saving || !canSubmitForm">
          {{ saving ? 'Saving entry...' : 'Save Entry' }}
        </button>
        <button type="button" class="btn btn-muted" @click="resetForm" :disabled="saving">Clear</button>
      </div>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>
  </form>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

const OTHER_SUB_AREA_VALUE = '__OTHER_SUB_AREA__'

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
const form = reactive({ attribute_id: '', sub_area_id: '', custom_sub_area_name: '', grade_code: '', remarks: '' })
const attributeSearch = ref('')
const subAreaSearch = ref('')
const attributeOpen = ref(false)
const subAreaOpen = ref(false)

const selectedAttribute = computed(() => props.attributes.find((a) => Number(a.id) === Number(form.attribute_id)) || null)
const isOtherSubArea = computed(() => form.sub_area_id === OTHER_SUB_AREA_VALUE)
const selectedSubArea = computed(() => {
  if (isOtherSubArea.value) {
    return {
      id: OTHER_SUB_AREA_VALUE,
      name: form.custom_sub_area_name || subAreaSearch.value || 'Other sub-area',
      photo_min_required: 1,
      photo_max_allowed: 3,
      video_required: false,
      video_max_seconds: 15,
      is_custom: true,
    }
  }
  return props.subAreas.find((s) => Number(s.id) === Number(form.sub_area_id)) || null
})
const photoMinRequired = computed(() => Math.max(1, Number(selectedSubArea.value?.photo_min_required || 1)))
const photoMaxAllowed = computed(() => Math.max(photoMinRequired.value, Number(selectedSubArea.value?.photo_max_allowed || 3)))
const evidenceHelpText = computed(() => `Photo evidence is mandatory: ${photoMinRequired.value} required, up to ${photoMaxAllowed.value} allowed. Video remains optional.`)
const customSubAreaReady = computed(() => !isOtherSubArea.value || form.custom_sub_area_name.trim().length >= 2)
const canSubmitForm = computed(() => Boolean(
  props.canSave
  && form.attribute_id
  && selectedSubArea.value
  && customSubAreaReady.value
  && form.grade_code
  && !props.saving
))
const localSaveBlockedText = computed(() => {
  if (!form.attribute_id) return 'Select attribute first'
  if (!selectedSubArea.value) return 'Select sub-area first'
  if (isOtherSubArea.value && !customSubAreaReady.value) return 'Enter Other sub-area name'
  if (!form.grade_code) return 'Select grade first'
  return props.saveBlockedText
})
const subAreaPlaceholder = computed(() => {
  if (!form.attribute_id) return 'Select attribute first'
  if (props.loadingSubAreas) return 'Loading sub-areas...'
  return 'Type sub-area keyword or choose Other'
})
const filteredAttributes = computed(() => filterList(props.attributes, attributeSearch.value, ['name', 'code', 'description']))
const filteredSubAreas = computed(() => filterList(props.subAreas, subAreaSearch.value, ['name', 'code']))
const otherOptionLabel = computed(() => {
  const typed = subAreaSearch.value.trim()
  return typed ? `Other: ${typed}` : 'Other sub-area not in list'
})

function filterList(list, query, keys) {
  const q = String(query || '').trim().toLowerCase()
  if (!q) return list
  return list.filter((item) => keys.some((key) => String(item?.[key] || '').toLowerCase().includes(q)))
}

function subAreaOptionMeta(subArea) {
  const required = Number(subArea.photo_min_required || 0)
  const max = Number(subArea.photo_max_allowed || 0)
  const photoText = required ? `${required} mandatory photo${required === 1 ? '' : 's'}` : 'Photo rule not set'
  return max ? `${photoText} · max ${max}` : photoText
}

function onAttributeSearchInput() {
  form.attribute_id = ''
  form.sub_area_id = ''
  form.custom_sub_area_name = ''
  subAreaSearch.value = ''
  emit('sub-area-change', null)
  emit('attribute-change', null)
  attributeOpen.value = true
}

function selectAttribute(attribute) {
  form.attribute_id = Number(attribute.id)
  attributeSearch.value = attribute.name || ''
  form.sub_area_id = ''
  form.custom_sub_area_name = ''
  subAreaSearch.value = ''
  attributeOpen.value = false
  emit('sub-area-change', null)
  emit('attribute-change', Number(attribute.id))
}

function onSubAreaSearchInput() {
  form.sub_area_id = ''
  form.custom_sub_area_name = ''
  emit('sub-area-change', null)
  subAreaOpen.value = true
}

function selectSubArea(subArea) {
  form.sub_area_id = Number(subArea.id)
  form.custom_sub_area_name = ''
  subAreaSearch.value = subAreaOptionLabel(subArea)
  subAreaOpen.value = false
  emit('sub-area-change', selectedSubArea.value)
}

function selectOtherSubArea() {
  const typed = subAreaSearch.value.trim()
  form.sub_area_id = OTHER_SUB_AREA_VALUE
  form.custom_sub_area_name = typed
  subAreaSearch.value = typed || 'Other sub-area'
  subAreaOpen.value = false
  emit('sub-area-change', selectedSubArea.value)
}

function onCustomSubAreaInput() {
  emit('sub-area-change', selectedSubArea.value)
}

function closeAttributeMenuSoon() {
  window.setTimeout(() => { attributeOpen.value = false }, 160)
}

function closeSubAreaMenuSoon() {
  window.setTimeout(() => { subAreaOpen.value = false }, 160)
}

function subAreaOptionLabel(subArea){
  const required = Number(subArea.photo_min_required || 0)
  if (!required) return subArea.name
  return `${subArea.name} · ${required} photo${required === 1 ? '' : 's'}`
}

function submitEntry(){
  if (!canSubmitForm.value || props.saving) return
  const isCustom = isOtherSubArea.value
  emit('save', {
    attribute_id: Number(form.attribute_id),
    sub_area_id: isCustom ? null : Number(form.sub_area_id),
    custom_sub_area_name: isCustom ? form.custom_sub_area_name.trim() : null,
    grade_code: form.grade_code,
    remarks: form.remarks,
  })
}

function resetForm(){
  form.attribute_id = ''
  form.sub_area_id = ''
  form.custom_sub_area_name = ''
  form.grade_code = ''
  form.remarks = ''
  attributeSearch.value = ''
  subAreaSearch.value = ''
  attributeOpen.value = false
  subAreaOpen.value = false
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
.search-field { position:relative; min-width:0; }
.searchable-select { position:relative; }
.searchable-select.disabled { opacity:.72; }
.option-panel { position:absolute; z-index:30; left:0; right:0; top:calc(100% + 6px); max-height:280px; overflow:auto; border:1px solid #cbd5e1; border-radius:16px; background:#fff; box-shadow:0 18px 44px rgba(15,23,42,.18); padding:6px; }
.option-row { width:100%; display:grid; gap:3px; text-align:left; border:0; border-radius:12px; background:#fff; padding:10px 11px; cursor:pointer; color:#0f172a; }
.option-row:hover,
.option-row:focus { background:#eff6ff; outline:none; }
.option-row strong { font-size:13px; }
.option-row small { color:#64748b; font-weight:700; line-height:1.35; }
.other-option { border:1px dashed #93c5fd; background:#f8fbff; margin-top:5px; }
.option-empty { padding:12px; color:#64748b; font-weight:800; }
.field-hint { margin:6px 0 0; color:#64748b; font-size:12px; line-height:1.35; }
.other-sub-area-box { border:1px solid #bfdbfe; border-radius:16px; background:#f8fbff; padding:12px; display:grid; gap:7px; }
.entry-actions { border:1px solid #e5e7eb; border-radius:18px; padding:14px; display:flex; gap:14px; align-items:center; justify-content:space-between; background:#f8fafc; }
.entry-actions.ready { border-color:#bbf7d0; background:#f0fdf4; }
.save-status { display:grid; gap:3px; min-width:0; }
.save-status strong { color:#0f172a; font-size:14px; }
.save-status span { color:#64748b; font-size:12px; line-height:1.45; }
.button-row { display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end; }
.error-text { color:#b91c1c; font-weight:800; margin:0; }
button:disabled { opacity:.58; cursor:not-allowed; }
@media(max-width:760px){ .entry-actions{display:grid;} .button-row{justify-content:stretch;} .button-row .btn{width:100%;} .option-panel{max-height:240px;} }
</style>
