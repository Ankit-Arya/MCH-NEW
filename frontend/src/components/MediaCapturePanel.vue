<template>
  <div class="media-panel">
    <div class="media-actions">
      <label class="capture-btn required">
        Capture / Select Photo
        <input type="file" accept="image/*" capture="environment" @change="onPhoto" />
      </label>
      <label class="capture-btn optional">
        Optional Video
        <input type="file" accept="video/*" capture="environment" @change="onVideo" />
      </label>
    </div>
    <div class="preview-grid" v-if="photo || video">
      <div class="preview-card" v-if="photo">
        <strong>Photo selected</strong>
        <span>{{ photo.name }}</span>
      </div>
      <div class="preview-card" v-if="video">
        <strong>Video selected</strong>
        <span>{{ video.name }}</span>
      </div>
    </div>
    <p class="muted small">Photo is mandatory for each saved entry. Video is optional.</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const emit = defineEmits(['change'])
const photo = ref(null)
const video = ref(null)
function notify(){ emit('change', { photo: photo.value, video: video.value }) }
function onPhoto(e){ photo.value = e.target.files?.[0] || null; notify() }
function onVideo(e){ video.value = e.target.files?.[0] || null; notify() }
function reset(){ photo.value = null; video.value = null; notify() }
defineExpose({ reset })
</script>

<style scoped>
.media-panel { display:grid; gap:12px; }
.media-actions { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.capture-btn { display:flex; align-items:center; justify-content:center; border:1px dashed #9fb5d7; background:#f8fbff; min-height:74px; border-radius:18px; font-weight:900; color:#092b6f; cursor:pointer; text-align:center; }
.capture-btn.required { border-color:#0f4ca3; }
.capture-btn.optional { color:#475569; }
.capture-btn input { display:none; }
.preview-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.preview-card { border:1px solid #e6edf7; border-radius:14px; padding:10px; background:white; overflow:hidden; }
.preview-card strong { display:block; margin-bottom:3px; }
.preview-card span { color:#64748b; font-size:12px; word-break:break-all; }
@media(max-width:760px){ .media-actions,.preview-grid{grid-template-columns:1fr;} }
</style>
