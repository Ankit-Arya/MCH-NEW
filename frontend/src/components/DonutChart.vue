<template>
  <div class="donut-wrap" aria-label="Donut chart">
    <svg class="donut-svg" width="176" height="176" viewBox="0 0 42 42" role="img">
      <defs>
        <linearGradient id="softDonutGrad" x1="0" x2="1">
          <stop offset="0" stop-color="#93c5fd" />
          <stop offset="0.55" stop-color="#99f6e4" />
          <stop offset="1" stop-color="#c4b5fd" />
        </linearGradient>
      </defs>
      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="#edf2f7" stroke-width="6"></circle>
      <circle
        cx="21"
        cy="21"
        r="15.915"
        fill="transparent"
        stroke="url(#softDonutGrad)"
        stroke-width="6"
        :stroke-dasharray="dash"
        stroke-dashoffset="25"
        stroke-linecap="round"
      ></circle>
      <text x="21" y="20" text-anchor="middle" font-size="7" font-weight="800" fill="#0f172a">{{ value }}%</text>
      <text x="21" y="27" text-anchor="middle" font-size="3.4" fill="#64748b">{{ label }}</text>
    </svg>
    <div class="legend"><slot /></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ value: { type: Number, default: 0 }, label: { type: String, default: 'Score' } })
const clamped = computed(() => Math.max(0, Math.min(100, Number(props.value || 0))))
const dash = computed(() => `${clamped.value} ${100 - clamped.value}`)
</script>

<style scoped>
.donut-wrap {
  display: flex;
  gap: 18px;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
}

.donut-svg {
  filter: drop-shadow(0 10px 18px rgba(15, 23, 42, 0.07));
}

.legend {
  min-width: 160px;
  max-width: 100%;
  color: #475569;
}

@media (max-width: 640px) {
  .donut-wrap { gap: 10px; }
  .donut-svg { width: 148px; height: 148px; }
  .legend { min-width: 0; width: 100%; text-align: center; }
}
</style>
