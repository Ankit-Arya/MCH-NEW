
<template>
  <div class="simple-chart">
    <div v-if="!items.length" class="muted">No data available for selected filters.</div>
    <div v-for="item in items" :key="item.label" class="bar-row">
      <div class="bar-label">{{ item.label }}</div>
      <div class="bar-track"><span :style="{ width: normalized(item.value) + '%' }"></span></div>
      <div class="bar-value">{{ formatValue(item.value) }}</div>
    </div>
  </div>
</template>
<script setup>
const props = defineProps({ items: { type: Array, default: () => [] }, suffix: { type: String, default: '' } })
const max = () => Math.max(1, ...props.items.map(i => Number(i.value || 0)))
const normalized = (v) => Math.max(4, Math.round(Number(v || 0) / max() * 100))
const formatValue = (v) => `${Number(v || 0).toFixed(Number(v || 0) % 1 ? 1 : 0)}${props.suffix}`
</script>
<style scoped>
.simple-chart { display:grid; gap:12px; }
.bar-row { display:grid; grid-template-columns: 148px 1fr 72px; gap:12px; align-items:center; }
.bar-label { font-size:12px; color:#475569; font-weight:800; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bar-track { height:13px; background:#e8eef7; border-radius:999px; overflow:hidden; }
.bar-track span { display:block; height:100%; border-radius:inherit; background: linear-gradient(90deg, #d71920, #0f4ca3); }
.bar-value { text-align:right; font-weight:900; color:#0f172a; }
@media(max-width: 640px){ .bar-row { grid-template-columns: 90px 1fr 54px; } }
</style>
