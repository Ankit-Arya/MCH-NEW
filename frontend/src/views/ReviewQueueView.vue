<template>
  <AppLayout>
    <h1>Review Queue</h1>
    <div class="card">
      <table class="table">
        <thead><tr><th>No</th><th>Station</th><th>Type</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>
          <tr v-for="i in rows" :key="i.id">
            <td>{{ i.inspection_no }}</td><td>{{ i.station_id }}</td><td>{{ i.inspection_type }}</td><td><span class="badge">{{ i.status }}</span></td>
            <td><button class="btn btn-primary" @click="recommend(i)">Recommend/Approve</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'
const rows = ref([])
onMounted(async()=>{ rows.value = (await api.get('/reviews/pending')).data })
async function recommend(i){
  let endpoint = '/reviews/' + i.id + '/line-manager'
  let payload = { action: 'RECOMMEND_PENALTY', comments: 'Reviewed and recommended from frontend.', recommended_penalty_amount: 0 }
  if (i.status === 'LINE_MANAGER_RECOMMENDED') { endpoint = '/reviews/' + i.id + '/dgm'; payload = { action: 'APPROVE', comments: 'Approved by DGM.', final_penalty_amount: 0 } }
  if (i.status === 'GM_REVIEW_REQUIRED') { endpoint = '/reviews/' + i.id + '/gm'; payload = { action: 'GM_REVIEW', comments: 'Reviewed by GM.' } }
  await api.post(endpoint, payload)
  rows.value = (await api.get('/reviews/pending')).data
}
</script>
