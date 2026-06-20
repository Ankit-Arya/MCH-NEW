<template>
  <div class="card flat saved-card">
    <div class="card-title">
      <div>
        <h2>Saved Entries</h2>
        <p class="muted">These entries belong to the same inspection record.</p>
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
          <button v-if="canEdit" class="btn btn-sm btn-danger" @click="$emit('delete', entry)">Delete</button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
defineProps({ entries: { type:Array, default:()=>[] }, canEdit: { type:Boolean, default:true } })
defineEmits(['delete'])
function formatDate(value){ return value ? new Date(value).toLocaleString() : '-' }
function requiredPhotos(entry){ return Math.max(1, Number(entry.photo_min_required || 1)) }
function hasRequiredPhotos(entry){ return Number(entry.photo_count || 0) >= requiredPhotos(entry) }
function photoLabel(entry){
  const required = requiredPhotos(entry)
  const count = Number(entry.photo_count || 0)
  return required > 1 ? `${count}/${required}` : count
}
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
@media(max-width:760px){ .entry-row{display:grid;} .entry-side{justify-content:flex-start;} }
</style>
