<template>
  <div class="line-chart-shell" aria-label="Line chart">
    <svg class="line-chart" viewBox="0 0 700 240" preserveAspectRatio="none" role="img">
      <defs>
        <linearGradient id="softLineGrad" x1="0" x2="1">
          <stop offset="0" stop-color="#93c5fd" />
          <stop offset="0.55" stop-color="#99f6e4" />
          <stop offset="1" stop-color="#c4b5fd" />
        </linearGradient>
        <linearGradient id="softAreaGrad" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stop-color="#93c5fd" stop-opacity="0.26" />
          <stop offset="1" stop-color="#93c5fd" stop-opacity="0.03" />
        </linearGradient>
      </defs>

      <line
        v-for="n in 5"
        :key="n"
        x1="44"
        x2="680"
        :y1="gridY(n)"
        :y2="gridY(n)"
        stroke="#e8eef7"
        stroke-width="1"
      />

      <polygon v-if="areaPoints" :points="areaPoints" fill="url(#softAreaGrad)" />
      <polyline
        v-if="points.length"
        :points="points"
        fill="none"
        stroke="url(#softLineGrad)"
        stroke-width="4"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <circle
        v-for="p in pointList"
        :key="p.label"
        :cx="p.x"
        :cy="p.y"
        r="4.6"
        fill="#ffffff"
        stroke="#60a5fa"
        stroke-width="2.4"
      />

      <g v-for="p in labelList" :key="p.label">
        <text :x="p.x" y="226" text-anchor="middle" font-size="11" fill="#64748b">{{ p.label }}</text>
      </g>
      <text x="46" y="18" font-size="11" fill="#64748b">100%</text>
      <text x="46" y="198" font-size="11" fill="#64748b">0%</text>
      <text v-if="!items.length" x="350" y="120" text-anchor="middle" fill="#64748b">No trend data</text>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ items: { type: Array, default: () => [] } })

const xFor = (i) => 44 + (props.items.length <= 1 ? 0 : i * (636 / (props.items.length - 1)))
const yFor = (v) => 202 - Math.max(0, Math.min(100, Number(v || 0))) * 1.82
const pointList = computed(() => props.items.map((item, i) => ({ label: item.label, x: xFor(i), y: yFor(item.value) })))
const points = computed(() => pointList.value.map(p => `${p.x},${p.y}`).join(' '))
const areaPoints = computed(() => {
  if (!pointList.value.length) return ''
  const first = pointList.value[0]
  const last = pointList.value[pointList.value.length - 1]
  return `${first.x},202 ${points.value} ${last.x},202`
})
const labelList = computed(() => pointList.value.filter((_, i) => props.items.length < 9 || i % Math.ceil(props.items.length / 8) === 0))
const gridY = (n) => 20 + n * 36
</script>

<style scoped>
.line-chart-shell {
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
}

.line-chart {
  width: 100%;
  height: 260px;
  display: block;
}

@media (max-width: 640px) {
  .line-chart { height: 220px; }
}
</style>
