<template>
  <div class="simple-chart" aria-label="Bar chart">
    <div v-if="!items.length" class="chart-empty">No data available for selected filters.</div>

    <div
      v-for="(item, index) in items"
      :key="item.label || index"
      class="bar-row"
      :style="rowStyle(index)"
    >
      <div class="bar-label" :title="item.label">{{ item.label }}</div>
      <div class="bar-track" aria-hidden="true">
        <span :style="{ width: normalized(item.value) + '%' }"></span>
      </div>
      <div class="bar-value">{{ formatValue(item.value) }}</div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  items: { type: Array, default: () => [] },
  suffix: { type: String, default: '' }
})

const palette = [
  { fill: '#93c5fd', fill2: '#bfdbfe', text: '#1e3a8a' },
  { fill: '#99f6e4', fill2: '#ccfbf1', text: '#115e59' },
  { fill: '#c4b5fd', fill2: '#ddd6fe', text: '#5b21b6' },
  { fill: '#fcd34d', fill2: '#fde68a', text: '#92400e' },
  { fill: '#f9a8d4', fill2: '#fbcfe8', text: '#9d174d' },
  { fill: '#a7f3d0', fill2: '#d1fae5', text: '#065f46' }
]

const max = () => Math.max(1, ...props.items.map(i => Number(i.value || 0)))
const normalized = (v) => Math.max(4, Math.round(Number(v || 0) / max() * 100))
const formatValue = (v) => `${Number(v || 0).toFixed(Number(v || 0) % 1 ? 1 : 0)}${props.suffix}`
const rowStyle = (index) => {
  const item = palette[index % palette.length]
  return {
    '--bar-fill': item.fill,
    '--bar-fill-2': item.fill2,
    '--bar-text': item.text
  }
}
</script>

<style scoped>
.simple-chart {
  display: grid;
  gap: 14px;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
}

.chart-empty {
  color: #64748b;
  font-size: 14px;
  padding: 18px;
  border: 1px dashed #dbe4ef;
  border-radius: 16px;
  background: #f8fafc;
}

.bar-row {
  display: grid;
  grid-template-columns: minmax(90px, 150px) minmax(0, 1fr) minmax(48px, 72px);
  gap: 12px;
  align-items: center;
  min-width: 0;
}

.bar-label {
  font-size: 12px;
  color: #475569;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  height: 14px;
  background: linear-gradient(180deg, #f1f5f9, #e8eef7);
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
  min-width: 0;
}

.bar-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--bar-fill), var(--bar-fill-2));
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.28);
}

.bar-value {
  text-align: right;
  font-weight: 900;
  color: var(--bar-text);
  font-size: 13px;
  white-space: nowrap;
}

@media (max-width: 640px) {
  .simple-chart { gap: 12px; }
  .bar-row {
    grid-template-columns: minmax(72px, 98px) minmax(0, 1fr) minmax(42px, 56px);
    gap: 9px;
  }
  .bar-label { font-size: 11px; }
  .bar-value { font-size: 12px; }
  .bar-track { height: 12px; }
}
</style>
