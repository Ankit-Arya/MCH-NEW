<template>
  <AppLayout>
    <section class="card hero-panel help-hero">
      <div>
        <h1>Help Forum</h1>
        <p class="hero-subtitle">
          Ask questions, search earlier answers, upload screenshots/videos/PDFs and continue discussion like a shared support forum.
        </p>
      </div>
      <button class="btn btn-primary" type="button" @click="showCreate = !showCreate">
        {{ showCreate ? 'Close Question Form' : 'Ask a Question' }}
      </button>
    </section>

    <section v-if="showCreate" class="card section-gap create-card">
      <div class="card-title">
        <div>
          <h2>Submit a new question</h2>
          <p class="muted">Add enough detail so other users and admin can understand the issue. Attach images, videos or PDF if needed.</p>
        </div>
      </div>
      <form class="topic-form" @submit.prevent="createTopic">
        <label>
          <span class="label">Question title</span>
          <input class="input" v-model.trim="newTopic.title" required maxlength="240" placeholder="Example: Photo upload failed for platform area" />
        </label>
        <label>
          <span class="label">Details</span>
          <textarea class="input" v-model.trim="newTopic.body" required rows="5" maxlength="5000" placeholder="Describe the problem, screen, station, role, or steps followed"></textarea>
        </label>
        <label>
          <span class="label">Upload media</span>
          <input class="input" type="file" multiple accept="image/*,video/*,application/pdf" @change="onNewTopicFiles" />
          <small class="muted">Allowed: image, video and PDF files.</small>
        </label>
        <div class="form-actions">
          <button class="btn btn-primary" type="submit" :disabled="creatingTopic">{{ creatingTopic ? 'Submitting...' : 'Submit Question' }}</button>
          <button class="btn btn-muted" type="button" @click="resetNewTopic" :disabled="creatingTopic">Clear</button>
        </div>
      </form>
    </section>

    <section class="forum-layout section-gap">
      <div class="card forum-list-card">
        <div class="card-title list-title">
          <div>
            <h2>Questions</h2>
            <p class="muted small-text" v-if="pagination.total">Showing {{ pagination.from_record }}–{{ pagination.to_record }} of {{ pagination.total }}</p>
            <p class="muted small-text" v-else>No questions found</p>
          </div>
        </div>

        <div class="search-bar">
          <input
            class="input"
            v-model.trim="filters.search"
            placeholder="Search question, answer or comment"
            @keyup.enter="searchTopics"
          />
          <select class="input status-filter" v-model="filters.status" @change="searchTopics">
            <option value="ALL">All</option>
            <option value="OPEN">Open</option>
            <option value="ANSWERED">Answered</option>
            <option value="CLOSED">Closed</option>
          </select>
          <button class="btn btn-secondary" type="button" @click="searchTopics" :disabled="loading">Search</button>
        </div>

        <div class="topic-list">
          <button
            v-for="topic in topics"
            :key="topic.id"
            class="topic-card"
            :class="{ active: selectedTopic?.id === topic.id }"
            type="button"
            @click="selectTopic(topic)"
          >
            <div class="topic-card-head">
              <strong>{{ topic.title }}</strong>
              <span class="badge" :class="statusClass(topic.status)">{{ statusLabel(topic.status) }}</span>
            </div>
            <p>{{ topic.body }}</p>
            <div class="topic-meta">
              <span>{{ topic.created_by_user?.name || 'User' }}</span>
              <span>{{ formatDateTime(topic.updated_at || topic.created_at) }}</span>
              <span>{{ topic.comment_count }} comment{{ topic.comment_count === 1 ? '' : 's' }}</span>
              <span v-if="topic.media_count">{{ topic.media_count }} attachment{{ topic.media_count === 1 ? '' : 's' }}</span>
            </div>
          </button>
          <div v-if="!topics.length && !loading" class="empty-state">No matching question found. Ask a new question if this has not been discussed yet.</div>
        </div>

        <div class="pagination-bar" v-if="pagination.total > 0">
          <button class="btn btn-outline" type="button" @click="goPrev" :disabled="!pagination.has_prev || loading">Previous</button>
          <span>Page {{ pagination.page }} of {{ pagination.pages }}</span>
          <button class="btn btn-outline" type="button" @click="goNext" :disabled="!pagination.has_next || loading">Next</button>
        </div>
      </div>

      <div class="card topic-detail-card">
        <div v-if="!selectedTopic" class="empty-detail">
          <h2>Select a question</h2>
          <p class="muted">Choose any question from the left side to view discussion, attachments and admin answer.</p>
        </div>

        <template v-else>
          <div class="detail-header">
            <div>
              <p class="muted small-text">Asked by {{ selectedTopic.created_by_user?.name || 'User' }}</p>
              <h2>{{ selectedTopic.title }}</h2>
              <div class="detail-badges">
                <span class="badge" :class="statusClass(selectedTopic.status)">{{ statusLabel(selectedTopic.status) }}</span>
                <span class="badge blue">{{ selectedTopic.view_count || 0 }} views</span>
                <span class="badge">{{ selectedTopic.comment_count || 0 }} comments</span>
              </div>
            </div>
            <button v-if="isAdmin && selectedTopic.status !== 'CLOSED'" class="btn btn-outline" type="button" @click="setStatus('CLOSED')">Close</button>
          </div>

          <article class="question-body">
            <p>{{ selectedTopic.body }}</p>
            <MediaList :items="selectedTopic.media_files" @preview="previewMedia" />
          </article>

          <section class="comments-section">
            <h3>Discussion</h3>
            <article
              v-for="comment in selectedTopic.comments || []"
              :key="comment.id"
              class="comment-card"
              :class="{ answer: comment.is_admin_answer }"
            >
              <div class="comment-head">
                <div>
                  <strong>{{ comment.created_by_user?.name || 'User' }}</strong>
                  <span>{{ roleLabel(comment.created_by_user?.role) }} · {{ formatDateTime(comment.created_at) }}</span>
                </div>
                <span v-if="comment.is_admin_answer" class="badge green">Admin answer</span>
              </div>
              <p>{{ comment.body }}</p>
              <MediaList :items="comment.media_files" @preview="previewMedia" />
            </article>
            <p v-if="!selectedTopic.comments?.length" class="muted">No comments yet.</p>
          </section>

          <section v-if="isAdmin" class="reply-box admin-box">
            <h3>Admin answer</h3>
            <textarea class="input" v-model.trim="answerForm.body" rows="4" placeholder="Write official answer / solution"></textarea>
            <input class="input" type="file" multiple accept="image/*,video/*,application/pdf" @change="onAnswerFiles" />
            <div class="form-actions">
              <button class="btn btn-primary" type="button" @click="submitAnswer" :disabled="!answerForm.body || answering">{{ answering ? 'Posting...' : 'Post Admin Answer' }}</button>
            </div>
          </section>

          <section class="reply-box">
            <h3>Add comment</h3>
            <textarea class="input" v-model.trim="commentForm.body" rows="4" placeholder="Add your comment or follow-up"></textarea>
            <input class="input" type="file" multiple accept="image/*,video/*,application/pdf" @change="onCommentFiles" />
            <div class="form-actions">
              <button class="btn btn-secondary" type="button" @click="submitComment" :disabled="!commentForm.body || commenting">{{ commenting ? 'Posting...' : 'Post Comment' }}</button>
            </div>
          </section>
        </template>
      </div>
    </section>

    <section v-if="mediaPreview.open" class="media-modal-backdrop" @click.self="closeMediaPreview">
      <div class="media-modal-card">
        <div class="media-modal-header">
          <div>
            <p class="muted small-text">Attachment preview</p>
            <h2>{{ mediaPreview.name }}</h2>
          </div>
          <button class="btn btn-outline" type="button" @click="closeMediaPreview">Close</button>
        </div>
        <div class="media-preview-body">
          <img v-if="mediaPreview.type.startsWith('image/')" :src="mediaPreview.url" alt="Help media preview" />
          <video v-else-if="mediaPreview.type.startsWith('video/')" :src="mediaPreview.url" controls></video>
          <iframe v-else-if="mediaPreview.type === 'application/pdf'" :src="mediaPreview.url"></iframe>
          <a v-else class="btn btn-primary" :href="mediaPreview.url" target="_blank" rel="noopener">Open attachment</a>
        </div>
      </div>
    </section>

    <p v-if="error" class="error floating-error">{{ error }}</p>
  </AppLayout>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const topics = ref([])
const selectedTopic = ref(null)
const loading = ref(false)
const creatingTopic = ref(false)
const commenting = ref(false)
const answering = ref(false)
const showCreate = ref(false)
const error = ref('')

const filters = reactive({ search: '', status: 'ALL' })
const pagination = reactive({ page: 1, size: 20, total: 0, pages: 1, has_next: false, has_prev: false, from_record: 0, to_record: 0 })
const newTopic = reactive({ title: '', body: '' })
const commentForm = reactive({ body: '' })
const answerForm = reactive({ body: '' })
const newTopicFiles = ref([])
const commentFiles = ref([])
const answerFiles = ref([])
const mediaPreview = reactive({ open: false, url: '', name: '', type: '' })

const isAdmin = computed(() => ['SUPER_ADMIN', 'HK_CELL_ADMIN', 'GM_OPS'].includes(auth.user?.role))

const MediaList = defineComponent({
  name: 'MediaList',
  props: { items: { type: Array, default: () => [] } },
  emits: ['preview'],
  setup(props, { emit }) {
    return () => props.items?.length
      ? h('div', { class: 'media-list' }, props.items.map((item) => h('button', {
        class: 'media-chip',
        type: 'button',
        onClick: () => emit('preview', item)
      }, [attachmentIcon(item), ' ', item.original_file_name || 'Attachment'])))
      : null
  }
})

function attachmentIcon(item) {
  const type = String(item?.mime_type || '')
  if (type.startsWith('image/')) return '🖼️'
  if (type.startsWith('video/')) return '🎬'
  if (type === 'application/pdf') return '📄'
  return '📎'
}

function roleLabel(role) {
  const labels = {
    SUPER_ADMIN: 'Super Admin',
    HK_CELL_ADMIN: 'HK Cell Admin',
    GM_OPS: 'GM/Ops',
    DGM_LINE: 'DGM Line',
    DGM_HK: 'DGM HK',
    AM_MGR_LINE: 'Line Manager',
    AM_MGR_HK: 'HK Manager',
    STATION_MANAGER: 'Station Manager',
    EIT_MEMBER: 'External Inspection Team',
    AUDITOR: 'Auditor'
  }
  return labels[role] || role || 'User'
}

function statusClass(status) {
  if (status === 'ANSWERED') return 'green'
  if (status === 'CLOSED') return 'blue'
  return 'amber'
}

function statusLabel(status) {
  const labels = { OPEN: 'Open', ANSWERED: 'Answered', CLOSED: 'Closed' }
  return labels[status] || status || '-'
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}

function applyPagination(data) {
  topics.value = data.items || []
  pagination.page = data.page || 1
  pagination.size = data.size || pagination.size
  pagination.total = data.total || 0
  pagination.pages = data.pages || 1
  pagination.has_next = Boolean(data.has_next)
  pagination.has_prev = Boolean(data.has_prev || data.has_previous)
  pagination.from_record = data.from_record || ((pagination.page - 1) * pagination.size + 1)
  pagination.to_record = data.to_record || Math.min(pagination.page * pagination.size, pagination.total)
  if (!pagination.total) { pagination.from_record = 0; pagination.to_record = 0 }
}

async function loadTopics() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/help/topics', {
      params: {
        search: filters.search || undefined,
        status: filters.status,
        page: pagination.page,
        size: pagination.size
      }
    })
    applyPagination(data)
    if (!selectedTopic.value && topics.value.length) await selectTopic(topics.value[0])
  } catch (e) {
    error.value = e.response?.data?.detail || 'Unable to load help forum'
  } finally {
    loading.value = false
  }
}

async function searchTopics() {
  pagination.page = 1
  selectedTopic.value = null
  await loadTopics()
}

async function goPrev() { if (pagination.has_prev) { pagination.page -= 1; await loadTopics() } }
async function goNext() { if (pagination.has_next) { pagination.page += 1; await loadTopics() } }

async function selectTopic(topic) {
  error.value = ''
  try {
    const { data } = await api.get(`/help/topics/${topic.id}`)
    selectedTopic.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Unable to open help topic'
  }
}

function onNewTopicFiles(event) { newTopicFiles.value = Array.from(event.target.files || []) }
function onCommentFiles(event) { commentFiles.value = Array.from(event.target.files || []) }
function onAnswerFiles(event) { answerFiles.value = Array.from(event.target.files || []) }

function resetNewTopic() {
  newTopic.title = ''
  newTopic.body = ''
  newTopicFiles.value = []
}

async function uploadFilesToTopic(topicId, files) {
  for (const file of files || []) {
    const fd = new FormData()
    fd.append('file', file, file.name)
    await api.post(`/help/topics/${topicId}/media`, fd)
  }
}

async function uploadFilesToComment(commentId, files) {
  for (const file of files || []) {
    const fd = new FormData()
    fd.append('file', file, file.name)
    await api.post(`/help/comments/${commentId}/media`, fd)
  }
}

async function createTopic() {
  if (!newTopic.title || !newTopic.body) return
  creatingTopic.value = true
  error.value = ''
  try {
    const { data } = await api.post('/help/topics', { title: newTopic.title, body: newTopic.body })
    await uploadFilesToTopic(data.id, newTopicFiles.value)
    resetNewTopic()
    showCreate.value = false
    pagination.page = 1
    await loadTopics()
    await selectTopic(data)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Unable to submit question'
  } finally {
    creatingTopic.value = false
  }
}

async function submitComment() {
  if (!selectedTopic.value || !commentForm.body) return
  commenting.value = true
  error.value = ''
  try {
    const { data } = await api.post(`/help/topics/${selectedTopic.value.id}/comments`, { body: commentForm.body })
    await uploadFilesToComment(data.id, commentFiles.value)
    commentForm.body = ''
    commentFiles.value = []
    await selectTopic(selectedTopic.value)
    await loadTopics()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Unable to post comment'
  } finally {
    commenting.value = false
  }
}

async function submitAnswer() {
  if (!selectedTopic.value || !answerForm.body) return
  answering.value = true
  error.value = ''
  try {
    const { data } = await api.post(`/help/topics/${selectedTopic.value.id}/answer`, { body: answerForm.body })
    await uploadFilesToComment(data.id, answerFiles.value)
    answerForm.body = ''
    answerFiles.value = []
    await selectTopic(selectedTopic.value)
    await loadTopics()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Unable to post admin answer'
  } finally {
    answering.value = false
  }
}

async function setStatus(status) {
  if (!selectedTopic.value) return
  error.value = ''
  try {
    const { data } = await api.patch(`/help/topics/${selectedTopic.value.id}/status`, { status })
    selectedTopic.value = data
    await loadTopics()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Unable to update topic status'
  }
}

function cleanupMediaUrl() {
  if (mediaPreview.url) {
    window.URL.revokeObjectURL(mediaPreview.url)
    mediaPreview.url = ''
  }
}

async function previewMedia(media) {
  cleanupMediaUrl()
  error.value = ''
  try {
    const { data } = await api.get(media.preview_url, { responseType: 'blob' })
    mediaPreview.url = window.URL.createObjectURL(data)
    mediaPreview.name = media.original_file_name || 'Attachment'
    mediaPreview.type = media.mime_type || data.type || 'application/octet-stream'
    mediaPreview.open = true
  } catch (e) {
    error.value = e.response?.data?.detail || 'Unable to preview attachment'
  }
}

function closeMediaPreview() {
  mediaPreview.open = false
  cleanupMediaUrl()
}

onMounted(loadTopics)
onBeforeUnmount(cleanupMediaUrl)
</script>

<style scoped>
.help-hero { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.create-card { display: grid; gap: 14px; }
.topic-form { display: grid; gap: 12px; }
.forum-layout { display: grid; grid-template-columns: minmax(340px, 0.9fr) minmax(420px, 1.25fr); gap: 18px; align-items: start; }
.forum-list-card, .topic-detail-card { min-height: 520px; }
.list-title { align-items: flex-start; }
.small-text { font-size: 0.9rem; margin-top: 4px; }
.search-bar { display: grid; grid-template-columns: 1fr 150px auto; gap: 10px; margin: 14px 0; }
.status-filter { min-width: 140px; }
.topic-list { display: grid; gap: 10px; }
.topic-card { display: grid; gap: 8px; width: 100%; text-align: left; border: 1px solid #dbe3f0; border-radius: 18px; background: #fff; padding: 14px; cursor: pointer; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05); }
.topic-card:hover, .topic-card.active { border-color: #93c5fd; background: #f8fbff; }
.topic-card-head { display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; }
.topic-card strong { color: #0f172a; line-height: 1.25; }
.topic-card p { margin: 0; color: #475569; line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.topic-meta { display: flex; flex-wrap: wrap; gap: 8px 12px; color: #64748b; font-size: 12px; font-weight: 800; }
.pagination-bar { display: flex; justify-content: flex-end; align-items: center; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
.empty-state, .empty-detail { border: 1px dashed #cbd5e1; border-radius: 18px; padding: 22px; color: #64748b; background: #f8fafc; }
.detail-header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; border-bottom: 1px solid #e2e8f0; padding-bottom: 14px; }
.detail-header h2 { margin: 2px 0 8px; color: #0f172a; }
.detail-badges { display: flex; flex-wrap: wrap; gap: 8px; }
.question-body { margin: 16px 0; padding: 14px; border: 1px solid #dbeafe; border-radius: 18px; background: #f8fbff; }
.question-body p, .comment-card p { margin: 0 0 10px; color: #334155; line-height: 1.55; white-space: pre-wrap; }
.comments-section { display: grid; gap: 12px; }
.comments-section h3, .reply-box h3 { margin: 0; color: #0f172a; }
.comment-card { display: grid; gap: 8px; border: 1px solid #e2e8f0; border-radius: 18px; padding: 14px; background: white; }
.comment-card.answer { border-color: #bbf7d0; background: #f0fdf4; }
.comment-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.comment-head strong { display: block; color: #0f172a; }
.comment-head span { display: block; color: #64748b; font-size: 12px; font-weight: 800; margin-top: 2px; }
.reply-box { display: grid; gap: 10px; margin-top: 18px; padding-top: 16px; border-top: 1px solid #e2e8f0; }
.admin-box { border: 1px solid #bbf7d0; border-radius: 18px; background: #f0fdf4; padding: 14px; }
.form-actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
.media-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.media-chip { border: 1px solid #dbe3f0; border-radius: 999px; background: #fff; color: #17345c; padding: 7px 10px; font-weight: 800; cursor: pointer; }
.media-chip:hover { border-color: #93c5fd; background: #eff6ff; }
.media-modal-backdrop { position: fixed; inset: 0; z-index: 4000; display: grid; place-items: center; padding: 18px; background: rgba(15,23,42,.48); backdrop-filter: blur(4px); }
.media-modal-card { width: min(880px, 100%); max-height: 92vh; overflow: auto; background: white; border-radius: 24px; padding: 18px; box-shadow: 0 28px 80px rgba(15,23,42,.28); }
.media-modal-header { display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 12px; }
.media-modal-header h2 { margin: 2px 0 0; font-size: 18px; }
.media-preview-body { display: grid; place-items: center; min-height: 240px; }
.media-preview-body img, .media-preview-body video { max-width: 100%; max-height: 70vh; border-radius: 14px; }
.media-preview-body iframe { width: 100%; height: 70vh; border: 0; border-radius: 14px; }
.error { color: #b91c1c; font-weight: 900; }
.floating-error { position: fixed; right: 22px; bottom: 22px; z-index: 5000; max-width: 520px; padding: 12px 14px; border-radius: 14px; background: #fee2e2; border: 1px solid #fecaca; }
@media (max-width: 980px) {
  .forum-layout { grid-template-columns: 1fr; }
  .help-hero { display: grid; }
  .search-bar { grid-template-columns: 1fr; }
  .detail-header, .media-modal-header { flex-direction: column; }
}


/* MOBILE-FIRST HELP FORUM PATCH */
@media (max-width: 760px) {
  .forum-list-card,
  .topic-detail-card { min-height: auto; }
  .topic-card-head,
  .comment-head,
  .detail-header,
  .media-modal-header { display: grid; grid-template-columns: 1fr; }
  .topic-card { padding: 12px; border-radius: 16px; }
  .topic-card p { -webkit-line-clamp: 3; }
  .topic-meta { display: grid; grid-template-columns: 1fr; gap: 4px; }
  .question-body,
  .comment-card,
  .admin-box { padding: 12px; border-radius: 16px; }
  .form-actions { display: grid; grid-template-columns: 1fr; justify-content: stretch; }
  .media-list { display: grid; grid-template-columns: 1fr; }
  .media-chip { width: 100%; border-radius: 14px; text-align: left; overflow-wrap: anywhere; }
  .media-modal-backdrop { padding: 10px; align-items: end; }
  .media-modal-card { width: 100%; max-height: calc(100svh - 20px); border-radius: 18px 18px 0 0; padding: 14px; }
  .media-preview-body { min-height: 180px; }
  .media-preview-body img,
  .media-preview-body video { max-height: 68svh; }
  .media-preview-body iframe { height: 72svh; }
  .floating-error { left: 10px; right: 10px; bottom: 10px; max-width: none; }
}
/* END MOBILE-FIRST HELP FORUM PATCH */
</style>
