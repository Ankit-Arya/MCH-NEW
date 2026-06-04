<template>
  <form class="entry-form" @submit.prevent="submitEntry">
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
        <select class="input" v-model="form.sub_area_id" required :disabled="!form.attribute_id || loadingSubAreas">
          <option value="">{{ loadingSubAreas ? 'Loading...' : 'Select sub-area' }}</option>
          <option v-for="s in subAreas" :key="s.id" :value="s.id">{{ s.name }}</option>
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
      <div>
        <label class="label">Entry Action</label>
        <div class="button-row">
          <button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? 'Saving...' : 'Save Entry' }}</button>
          <button type="button" class="btn btn-muted" @click="resetForm">Clear</button>
        </div>
      </div>
    </div>

    <div>
      <label class="label">Remarks</label>
      <textarea class="input" rows="3" v-model="form.remarks" placeholder="Write what was observed at this exact location/sub-area"></textarea>
    </div>

    <slot name="media"></slot>
    <slot name="metadata"></slot>

    <p v-if="error" class="error-text">{{ error }}</p>
  </form>
</template>

<script setup>
import { reactive, ref } from 'vue'
const props = defineProps({ attributes: Array, grades: Array, subAreas: Array, loadingSubAreas: Boolean, saving: Boolean, error: String })
const emit = defineEmits(['attribute-change', 'save', 'clear'])
const form = reactive({ attribute_id:'', sub_area_id:'', grade_code:'', remarks:'' })
function onAttributeChange(){ form.sub_area_id = ''; emit('attribute-change', Number(form.attribute_id)) }
function submitEntry(){ emit('save', { ...form, attribute_id:Number(form.attribute_id), sub_area_id:Number(form.sub_area_id) }) }
function resetForm(){ form.attribute_id=''; form.sub_area_id=''; form.grade_code=''; form.remarks=''; emit('clear') }
defineExpose({ resetForm })
</script>

<style scoped>
.entry-form { display:grid; gap:16px; }
.button-row { display:flex; gap:10px; flex-wrap:wrap; }
.error-text { color:#b91c1c; font-weight:800; margin:0; }
</style>
