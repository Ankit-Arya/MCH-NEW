<template>
  <AppLayout>
    <h1>Master Data</h1>
    <div class="grid grid-2">
      <section class="card"><h2>Stations</h2><ul><li v-for="s in data.stations" :key="s.id">{{ s.station_code }} - {{ s.station_name }}</li></ul></section>
      <section class="card"><h2>Contracts</h2><ul><li v-for="c in data.contracts" :key="c.id">{{ c.contract_code }} - {{ c.contract_name }}</li></ul></section>
      <section class="card"><h2>Attributes</h2><ul><li v-for="a in data.inspection_attributes" :key="a.id">{{ a.name }}</li></ul></section>
      <section class="card"><h2>Grading Schemes</h2><ul><li v-for="g in data.grading_schemes" :key="g.id">{{ g.name }}</li></ul></section>
    </div>
  </AppLayout>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'
const data = ref({ stations:[], contracts:[], inspection_attributes:[], grading_schemes:[] })
onMounted(async()=>{ data.value=(await api.get('/master/bootstrap')).data })
</script>
