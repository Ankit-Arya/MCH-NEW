
<template>
  <div class="donut-wrap">
    <svg width="176" height="176" viewBox="0 0 42 42">
      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="#e8eef7" stroke-width="6"></circle>
      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="#0f4ca3" stroke-width="6" :stroke-dasharray="dash" stroke-dashoffset="25" stroke-linecap="round"></circle>
      <text x="21" y="20" text-anchor="middle" font-size="7" font-weight="800" fill="#0f172a">{{ value }}%</text>
      <text x="21" y="27" text-anchor="middle" font-size="3.4" fill="#64748b">{{ label }}</text>
    </svg>
    <div class="legend"><slot /></div>
  </div>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ value: { type: Number, default: 0 }, label: { type: String, default: 'Score' } })
const dash = computed(() => `${Math.max(0, Math.min(100, props.value))} ${100 - Math.max(0, Math.min(100, props.value))}`)
</script>
<style scoped>
.donut-wrap { display:flex; gap:18px; align-items:center; justify-content:center; flex-wrap:wrap; }
.legend { min-width: 180px; }
</style>
