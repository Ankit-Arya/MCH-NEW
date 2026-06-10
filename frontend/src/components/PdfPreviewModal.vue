<template>
  <Teleport to="body">
    <div v-if="open" class="pdf-modal-backdrop" @click.self="$emit('close')">
      <section class="pdf-modal" role="dialog" aria-modal="true" :aria-label="title || 'PDF preview'">
        <header class="pdf-modal-header">
          <div>
            <p class="pdf-modal-eyebrow">PDF Preview</p>
            <h2>{{ title || 'Inspection PDF' }}</h2>
          </div>
          <div class="pdf-modal-actions">
            <a v-if="src" class="btn btn-outline" :href="src" target="_blank" rel="noopener">Open</a>
            <a v-if="src" class="btn btn-primary" :href="src" :download="downloadName || 'inspection.pdf'">Download</a>
            <button class="btn btn-ghost pdf-close" type="button" @click="$emit('close')" aria-label="Close PDF preview">✕</button>
          </div>
        </header>

        <div class="pdf-modal-body">
          <div v-if="loading" class="pdf-loading">
            <div class="pdf-spinner" aria-hidden="true"></div>
            <p>Preparing PDF preview...</p>
          </div>

          <iframe
            v-else-if="src"
            class="pdf-frame"
            :src="src"
            title="PDF preview"
          ></iframe>

          <div v-else class="pdf-empty">
            <p>PDF preview is not available.</p>
          </div>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  open: { type: Boolean, default: false },
  src: { type: String, default: '' },
  title: { type: String, default: '' },
  downloadName: { type: String, default: 'inspection.pdf' },
  loading: { type: Boolean, default: false }
})

defineEmits(['close'])
</script>

<style scoped>
.pdf-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 5000;
  background: rgba(15, 23, 42, 0.62);
  backdrop-filter: blur(5px);
  display: grid;
  place-items: center;
  padding: 20px;
}

.pdf-modal {
  width: min(1120px, 100%);
  height: min(86vh, 920px);
  background: #ffffff;
  border-radius: 24px;
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.35);
  border: 1px solid rgba(148, 163, 184, 0.28);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pdf-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.22);
  background: linear-gradient(135deg, #f8fbff 0%, #edf5ff 100%);
}

.pdf-modal-eyebrow {
  margin: 0 0 4px;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  font-weight: 800;
}

.pdf-modal-header h2 {
  margin: 0;
  font-size: 1.05rem;
  color: #0f172a;
}

.pdf-modal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.pdf-close {
  min-width: 42px;
  padding-inline: 12px;
}

.pdf-modal-body {
  flex: 1;
  min-height: 0;
  background: #f1f5f9;
}

.pdf-frame {
  width: 100%;
  height: 100%;
  border: 0;
  background: #ffffff;
}

.pdf-loading,
.pdf-empty {
  height: 100%;
  display: grid;
  place-items: center;
  color: #475569;
  font-weight: 700;
  text-align: center;
  gap: 12px;
}

.pdf-spinner {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  border: 4px solid rgba(37, 99, 235, 0.16);
  border-top-color: rgba(37, 99, 235, 0.72);
  animation: pdf-spin 0.8s linear infinite;
}

@keyframes pdf-spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 760px) {
  .pdf-modal-backdrop {
    padding: 0;
    align-items: stretch;
  }

  .pdf-modal {
    width: 100%;
    height: 100dvh;
    border-radius: 0;
  }

  .pdf-modal-header {
    align-items: flex-start;
    padding: 14px;
  }

  .pdf-modal-actions {
    gap: 6px;
  }

  .pdf-modal-actions .btn {
    padding: 8px 10px;
    font-size: 0.8rem;
  }

  .pdf-modal-header h2 {
    font-size: 0.95rem;
  }
}
</style>
