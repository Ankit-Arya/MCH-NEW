<template>
  <div class="metadata-card">
    <div class="metadata-title">
      <strong>Capture Metadata</strong>
      <button type="button" class="btn btn-sm btn-muted" @click="$emit('capture-gps')">Refresh GPS</button>
    </div>
    <div class="metadata-grid">
      <span><b>Latitude</b>{{ metadata.latitude ?? '-' }}</span>
      <span><b>Longitude</b>{{ metadata.longitude ?? '-' }}</span>
      <span><b>Accuracy</b>{{ metadata.gps_accuracy ? metadata.gps_accuracy.toFixed(1) + ' m' : '-' }}</span>
      <span><b>Captured At</b>{{ formattedTime }}</span>
    </div>
    <p v-if="error" class="error-text">{{ error }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ metadata: { type: Object, required: true }, error: { type: String, default: '' } })
defineEmits(['capture-gps'])
const formattedTime = computed(() => props.metadata.captured_at ? new Date(props.metadata.captured_at).toLocaleString() : '-')
</script>

<style scoped>
.metadata-card { background:#f8fbff; border:1px solid #dbe7f8; border-radius:18px; padding:14px; }
.metadata-title { display:flex; justify-content:space-between; gap:10px; align-items:center; margin-bottom:12px; }
.metadata-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }
.metadata-grid span { display:block; background:white; border:1px solid #e6edf7; border-radius:12px; padding:9px 10px; color:#334155; font-size:12px; }
.metadata-grid b { display:block; color:#64748b; font-size:11px; text-transform:uppercase; letter-spacing:.04em; margin-bottom:3px; }
.error-text { color:#b91c1c; font-weight:800; margin:10px 0 0; }
@media(max-width:760px){ .metadata-grid{grid-template-columns:1fr 1fr;} }
</style>
