<template>
  <div class="media-panel">
    <div class="media-summary">
      <strong>Photo evidence</strong>
      <span>
        {{ photos.length }} / {{ requiredCount }} mandatory selected
        <template v-if="maxCount"> · Max {{ maxCount }}</template>
      </span>
    </div>

    <div class="media-actions">
      <label class="capture-btn required" :class="{ disabled: hasReachedMax || processingPhotos }">
        {{ processingPhotos ? 'Preparing photo...' : (hasReachedMax ? 'Photo limit reached' : 'Capture / Add Photo') }}
        <input
          ref="photoInputRef"
          type="file"
          accept="image/*"
          capture="environment"
          multiple
          :disabled="hasReachedMax || processingPhotos"
          @change="onPhotos"
        />
      </label>
      <label class="capture-btn optional">
        Optional Video
        <input ref="videoInputRef" type="file" accept="video/*" capture="environment" @change="onVideo" />
      </label>
    </div>

    <p v-if="photoError" class="error-text small">{{ photoError }}</p>

    <div class="preview-grid" v-if="photos.length || video">
      <div class="preview-card photo-card" v-for="(item, index) in photos" :key="item.id">
        <div>
          <strong>Photo {{ index + 1 }}</strong>
          <span>{{ item.file.name }}</span>
          <em v-if="item.sizeNote">{{ item.sizeNote }}</em>
        </div>
        <button type="button" class="remove-btn" @click="removePhoto(index)">Remove</button>
      </div>
      <div class="preview-card" v-if="video">
        <div>
          <strong>Video selected</strong>
          <span>{{ video.name }}</span>
        </div>
        <button type="button" class="remove-btn" @click="removeVideo">Remove</button>
      </div>
    </div>

    <p class="muted small">
      Add photos one by one from mobile camera, or select multiple photos from gallery. Large camera photos are resized before upload so they do not cross the API photo-size limit.
    </p>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  photoMinRequired: { type: Number, default: 1 },
  photoMaxAllowed: { type: Number, default: 3 },
})

const emit = defineEmits(['change'])
const photos = ref([])
const video = ref(null)
const photoInputRef = ref(null)
const videoInputRef = ref(null)
const photoError = ref('')
const processingPhotos = ref(false)

const requiredCount = computed(() => Math.max(1, Number(props.photoMinRequired || 1)))
const maxCount = computed(() => Math.max(requiredCount.value, Number(props.photoMaxAllowed || requiredCount.value || 3)))
const hasReachedMax = computed(() => photos.value.length >= maxCount.value)

const COMPRESS_OVER_BYTES = 7 * 1024 * 1024
const MAX_IMAGE_DIMENSION = 1600
const JPEG_QUALITY = 0.82

function formatMb(bytes){
  if (!Number.isFinite(bytes)) return ''
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function notify(){
  const photoFiles = photos.value.map(item => item.file)
  emit('change', {
    photos: photoFiles,
    photo: photoFiles[0] || null, // backward-compatible shape for any older parent code
    video: video.value,
  })
}

function loadImage(file){
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Unable to read selected image'))
    }
    img.src = url
  })
}

function canvasToBlob(canvas, type, quality){
  return new Promise(resolve => canvas.toBlob(resolve, type, quality))
}

async function compressPhotoIfNeeded(file){
  if (!file?.type?.startsWith('image/') || file.size <= COMPRESS_OVER_BYTES) {
    return { file, sizeNote: `Size ${formatMb(file.size)}` }
  }

  try {
    const img = await loadImage(file)
    const sourceWidth = img.naturalWidth || img.width
    const sourceHeight = img.naturalHeight || img.height
    const largestSide = Math.max(sourceWidth, sourceHeight)
    const scale = largestSide > MAX_IMAGE_DIMENSION ? MAX_IMAGE_DIMENSION / largestSide : 1
    const targetWidth = Math.max(1, Math.round(sourceWidth * scale))
    const targetHeight = Math.max(1, Math.round(sourceHeight * scale))

    const canvas = document.createElement('canvas')
    canvas.width = targetWidth
    canvas.height = targetHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(img, 0, 0, targetWidth, targetHeight)

    const blob = await canvasToBlob(canvas, 'image/jpeg', JPEG_QUALITY)
    if (!blob) throw new Error('Unable to compress selected image')

    const baseName = (file.name || 'photo').replace(/\.[^.]+$/, '')
    const compressedFile = new File([blob], `${baseName}.jpg`, {
      type: 'image/jpeg',
      lastModified: Date.now(),
    })

    if (compressedFile.size >= file.size) {
      return { file, sizeNote: `Size ${formatMb(file.size)}` }
    }

    return {
      file: compressedFile,
      sizeNote: `Reduced ${formatMb(file.size)} → ${formatMb(compressedFile.size)}`,
    }
  } catch (_) {
    return {
      file,
      sizeNote: `Size ${formatMb(file.size)} · could not resize in browser`,
    }
  }
}

function makePhotoItem(file, sizeNote){
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}-${file.name}`,
    file,
    sizeNote,
  }
}

async function onPhotos(e){
  photoError.value = ''
  const selected = Array.from(e.target.files || [])
  e.target.value = ''
  if (!selected.length) return

  const remaining = maxCount.value - photos.value.length
  if (remaining <= 0) {
    photoError.value = `Maximum ${maxCount.value} photos allowed for this sub-area.`
    return
  }

  const accepted = selected.slice(0, remaining)
  processingPhotos.value = true
  try {
    const prepared = []
    for (const file of accepted) {
      const { file: preparedFile, sizeNote } = await compressPhotoIfNeeded(file)
      prepared.push(makePhotoItem(preparedFile, sizeNote))
    }

    photos.value = [...photos.value, ...prepared]

    if (selected.length > accepted.length) {
      photoError.value = `Only ${remaining} more photo${remaining === 1 ? '' : 's'} allowed. Extra files were ignored.`
    }
  } finally {
    processingPhotos.value = false
    notify()
  }
}

function onVideo(e){
  video.value = e.target.files?.[0] || null
  e.target.value = ''
  notify()
}

function removePhoto(index){
  photos.value.splice(index, 1)
  photoError.value = ''
  notify()
}

function removeVideo(){
  video.value = null
  if (videoInputRef.value) videoInputRef.value.value = ''
  notify()
}

function reset(){
  photos.value = []
  video.value = null
  photoError.value = ''
  processingPhotos.value = false
  if (photoInputRef.value) photoInputRef.value.value = ''
  if (videoInputRef.value) videoInputRef.value.value = ''
  notify()
}

defineExpose({ reset })
</script>

<style scoped>
.media-panel { display:grid; gap:12px; }
.media-summary { border:1px solid #dbeafe; background:#eff6ff; border-radius:16px; padding:10px 12px; display:flex; justify-content:space-between; gap:12px; align-items:center; }
.media-summary strong { color:#0f172a; font-size:14px; }
.media-summary span { color:#1d4ed8; font-size:12px; font-weight:900; }
.media-actions { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.capture-btn { display:flex; align-items:center; justify-content:center; border:1px dashed #9fb5d7; background:#f8fbff; min-height:74px; border-radius:18px; font-weight:900; color:#092b6f; cursor:pointer; text-align:center; padding:10px; }
.capture-btn.required { border-color:#0f4ca3; }
.capture-btn.optional { color:#475569; }
.capture-btn.disabled { opacity:.58; cursor:not-allowed; background:#f1f5f9; }
.capture-btn input { display:none; }
.preview-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.preview-card { border:1px solid #e6edf7; border-radius:14px; padding:10px; background:white; overflow:hidden; display:flex; justify-content:space-between; gap:10px; align-items:flex-start; }
.preview-card strong { display:block; margin-bottom:3px; }
.preview-card span { color:#64748b; font-size:12px; word-break:break-all; display:block; }
.preview-card em { color:#0f766e; font-size:11px; font-style:normal; font-weight:800; display:block; margin-top:4px; }
.remove-btn { border:0; border-radius:999px; background:#fee2e2; color:#991b1b; font-weight:900; font-size:11px; padding:5px 8px; cursor:pointer; flex:0 0 auto; }
.error-text { color:#b91c1c; font-weight:800; margin:0; }
@media(max-width:760px){ .media-actions,.preview-grid{grid-template-columns:1fr;} .media-summary{display:grid;} }
</style>
