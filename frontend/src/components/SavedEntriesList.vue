<template>
  <div class="card flat saved-card">
    <div class="card-title">
      <div>
        <h2>Saved Entries</h2>
        <p class="muted">These entries belong to the same inspection record. Open evidence preview before final submission.</p>
      </div>
      <span class="badge blue">{{ entries.length }} entries</span>
    </div>

    <div v-if="!entries.length" class="empty-state">
      No entries saved yet. Select an attribute and sub-area, capture mandatory photos, then save the entry.
    </div>

    <div v-else class="entry-list">
      <article v-for="entry in entries" :key="entry.id" class="entry-row">
        <div class="entry-main">
          <span class="badge">{{ entry.entry_no }}</span>
          <strong>{{ entry.attribute_name }} → {{ entry.sub_area_name }}</strong>
          <span class="muted small">{{ formatDate(entry.captured_at) }} · GPS {{ entry.captured_latitude ?? '-' }}, {{ entry.captured_longitude ?? '-' }}</span>
          <p v-if="entry.remarks">{{ entry.remarks }}</p>
        </div>
        <div class="entry-side">
          <span class="grade-pill">{{ entry.grade_code }} / {{ entry.grade_percentage }}%</span>
          <span :class="['badge', hasRequiredPhotos(entry) ? 'green' : 'red']">Photos {{ photoLabel(entry) }}</span>
          <span class="badge blue">Videos {{ entry.video_count }}</span>
          <button
            v-if="evidenceCount(entry)"
            class="btn btn-sm btn-outline"
            type="button"
            @click="openPreview(entry)"
          >
            Preview evidence
          </button>
          <button v-if="canEdit" class="btn btn-sm btn-danger" type="button" @click="$emit('delete', entry)">Delete</button>
        </div>
      </article>
    </div>

    <section v-if="preview.open" class="preview-backdrop" role="presentation" @click.self="closePreview">
      <div class="preview-modal" role="dialog" aria-modal="true" aria-labelledby="evidence-preview-title">
        <div class="preview-header">
          <div>
            <p class="muted small">Saved evidence preview</p>
            <h2 id="evidence-preview-title">{{ preview.title }}</h2>
            <p class="muted small">{{ preview.entryMeta }}</p>
          </div>
          <button class="btn btn-muted" type="button" @click="closePreview">Close</button>
        </div>

        <div v-if="preview.loading" class="preview-loading">Loading saved evidence...</div>
        <p v-else-if="preview.error" class="error-text">{{ preview.error }}</p>

        <div v-else class="preview-grid">
          <article v-for="item in preview.items" :key="item.id" class="preview-item">
            <div class="preview-media-frame">
              <img v-if="isPhoto(item)" :src="item.objectUrl" :alt="item.original_file_name || 'Inspection photo evidence'" />
              <video v-else-if="isVideo(item)" :src="item.objectUrl" controls playsinline preload="metadata"></video>
              <div v-else class="unsupported-preview">Preview not available for this file type.</div>
            </div>
            <div class="preview-caption">
              <strong>{{ mediaLabel(item) }}</strong>
              <span>{{ item.original_file_name || `Evidence #${item.id}` }}</span>
              <small>
                {{ formatFileSize(item.file_size) }}
                <template v-if="item.captured_at"> · {{ formatDate(item.captured_at) }}</template>
              </small>
            </div>
          </article>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, reactive } from 'vue'
import { api } from '../services/api'

const props = defineProps({
  entries: { type: Array, default: () => [] },
  canEdit: { type: Boolean, default: true }
})

defineEmits(['delete'])

const preview = reactive({
  open: false,
  loading: false,
  error: '',
  title: '',
  entryMeta: '',
  items: []
})

function formatDate(value) {
  return value ? new Date(value).toLocaleString('en-IN') : '-'
}

function requiredPhotos(entry) {
  return Math.max(1, Number(entry.photo_min_required || 1))
}

function hasRequiredPhotos(entry) {
  return Number(entry.photo_count || 0) >= requiredPhotos(entry)
}

function photoLabel(entry) {
  const required = requiredPhotos(entry)
  const count = Number(entry.photo_count || 0)
  return required > 1 ? `${count}/${required}` : count
}

function evidenceFiles(entry) {
  return Array.isArray(entry?.media_files) ? entry.media_files : []
}

function evidenceCount(entry) {
  const files = evidenceFiles(entry)
  if (files.length) return files.length
  return Number(entry?.photo_count || 0) + Number(entry?.video_count || 0)
}

function mediaTypeText(item) {
  return String(item?.media_type || '').toUpperCase()
}

function isPhoto(item) {
  return mediaTypeText(item) === 'PHOTO' || String(item?.mime_type || '').startsWith('image/')
}

function isVideo(item) {
  return mediaTypeText(item) === 'VIDEO' || String(item?.mime_type || '').startsWith('video/')
}

function mediaLabel(item) {
  if (isPhoto(item)) return 'Photo evidence'
  if (isVideo(item)) return 'Video evidence'
  return 'Evidence file'
}

function formatFileSize(bytes) {
  const size = Number(bytes || 0)
  if (!size) return 'Size unavailable'
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(2)} MB`
}

function revokePreviewUrls() {
  for (const item of preview.items || []) {
    if (item.objectUrl) window.URL.revokeObjectURL(item.objectUrl)
  }
  preview.items = []
}

function closePreview() {
  preview.open = false
  preview.loading = false
  preview.error = ''
  revokePreviewUrls()
}

async function openPreview(entry) {
  revokePreviewUrls()
  preview.open = true
  preview.loading = true
  preview.error = ''
  preview.title = `${entry.entry_no || 'Entry'} · ${entry.attribute_name || '-'}`
  preview.entryMeta = `${entry.sub_area_name || '-'} · ${entry.photo_count || 0} photo(s), ${entry.video_count || 0} video(s)`

  const files = evidenceFiles(entry)
  if (!files.length) {
    preview.loading = false
    preview.error = 'Evidence details are not available yet. Please refresh the inspection page and try again.'
    return
  }

  try {
    const loaded = []
    for (const file of files) {
      const previewUrl = file.preview_url
      if (!previewUrl) continue
      const { data } = await api.get(previewUrl, { responseType: 'blob' })
      loaded.push({
        ...file,
        objectUrl: window.URL.createObjectURL(data)
      })
    }
    preview.items = loaded
    if (!loaded.length) {
      preview.error = 'No previewable evidence found for this entry.'
    }
  } catch (error) {
    preview.error = error?.response?.data?.detail || 'Unable to load evidence preview.'
  } finally {
    preview.loading = false
  }
}

onBeforeUnmount(revokePreviewUrls)
</script>

<style scoped>
.saved-card { box-shadow:none; }
.empty-state { border:1px dashed #c8d6ec; background:#f8fbff; border-radius:18px; padding:22px; color:#64748b; font-weight:700; }
.entry-list { display:grid; gap:10px; }
.entry-row { display:flex; justify-content:space-between; gap:14px; align-items:flex-start; border:1px solid #e5edf8; border-radius:18px; padding:14px; background:#fff; }
.entry-main { display:grid; gap:5px; min-width:0; }
.entry-main p { margin:4px 0 0; color:#334155; }
.entry-side { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; align-items:center; }
.grade-pill { background:linear-gradient(135deg,#092b6f,#0f4ca3); color:white; border-radius:999px; padding:7px 10px; font-weight:900; font-size:12px; }

.preview-backdrop {
  position: fixed;
  inset: 0;
  z-index: 5000;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.54);
  backdrop-filter: blur(4px);
}

.preview-modal {
  width: min(980px, 100%);
  max-height: min(860px, 92vh);
  overflow: auto;
  border-radius: 26px;
  background: #fff;
  border: 1px solid #dbe3f0;
  box-shadow: 0 32px 90px rgba(15, 23, 42, 0.28);
  padding: 20px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 16px;
}

.preview-header h2 {
  margin: 4px 0;
  color: #0f172a;
}

.preview-loading,
.unsupported-preview {
  border: 1px dashed #cbd5e1;
  border-radius: 18px;
  background: #f8fafc;
  color: #64748b;
  font-weight: 800;
  padding: 26px;
  text-align: center;
}

.error-text { color:#b91c1c; font-weight:800; }

.preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.preview-item {
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  background: #f8fbff;
  overflow: hidden;
}

.preview-media-frame {
  display: grid;
  place-items: center;
  min-height: 220px;
  background: #0f172a;
}

.preview-media-frame img,
.preview-media-frame video {
  width: 100%;
  max-height: 420px;
  object-fit: contain;
  background: #0f172a;
}

.preview-caption {
  display: grid;
  gap: 3px;
  padding: 12px;
}

.preview-caption strong {
  color: #0f172a;
}

.preview-caption span {
  color: #475569;
  font-size: 13px;
  word-break: break-word;
}

.preview-caption small {
  color: #64748b;
  font-weight: 700;
}

@media(max-width:760px){
  .entry-row{display:grid;}
  .entry-side{justify-content:flex-start;}
  .preview-backdrop { padding: 10px; }
  .preview-modal { border-radius: 20px; padding: 14px; }
  .preview-header { display: grid; }
  .preview-grid { grid-template-columns: 1fr; }
}
</style>
