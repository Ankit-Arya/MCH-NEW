
<template>
  <div class="card stat-card">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">{{ value }}</div>
    <div v-if="foot" class="stat-foot">{{ foot }}</div>
  </div>
</template>
<script setup>
defineProps({ label: String, value: [String, Number], foot: String })
</script>
