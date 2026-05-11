<template>
  <AppLayout>
    <h1>Start Inspection</h1>
    <form class="card grid" @submit.prevent="start">
      <div class="grid grid-2">
        <div>
          <label class="label">Contract</label>
          <select class="input" v-model="form.contract_id" required>
            <option value="">Select contract</option>
            <option v-for="c in boot.contracts" :key="c.id" :value="c.id">{{ c.contract_name }}</option>
          </select>
        </div>
        <div>
          <label class="label">Station</label>
          <select class="input" v-model="form.station_id" required>
            <option value="">Select station</option>
            <option v-for="s in boot.stations" :key="s.id" :value="s.id">{{ s.station_name }}</option>
          </select>
        </div>
      </div>
      <div>
        <label class="label">Inspection Type</label>
        <select class="input" v-model="form.inspection_type">
          <option value="SM_INSPECTION">Station Manager Inspection</option>
          <option value="EIT_INSPECTION">External Inspection Team</option>
          <option value="SPECIAL_INSPECTION">Special Inspection</option>
        </select>
      </div>
      <div class="card mini">
        <strong>GPS</strong>
        <p>{{ gpsText }}</p>
        <button type="button" class="btn btn-muted" @click="captureGps">Capture GPS</button>
      </div>
      <textarea class="input" rows="3" v-model="form.remarks" placeholder="Initial remarks"></textarea>
      <button class="btn btn-primary">Start</button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </AppLayout>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'
import { api } from '../services/api'
const router = useRouter()
const boot = ref({ contracts: [], stations: [] })
const error = ref('')
const form = ref({ contract_id:'', station_id:'', inspection_type:'SM_INSPECTION', latitude:null, longitude:null, gps_accuracy:null, device_info:{ userAgent: navigator.userAgent }, remarks:'' })
const gpsText = computed(()=> form.value.latitude ? `${form.value.latitude}, ${form.value.longitude} accuracy ${form.value.gps_accuracy || '-'}m` : 'Not captured')
function captureGps(){
  navigator.geolocation.getCurrentPosition(pos => {
    form.value.latitude = pos.coords.latitude
    form.value.longitude = pos.coords.longitude
    form.value.gps_accuracy = pos.coords.accuracy
  }, () => { error.value = 'GPS permission denied or unavailable' }, { enableHighAccuracy: true, timeout: 10000 })
}
onMounted(async()=>{ boot.value = (await api.get('/master/bootstrap')).data })
async function start(){
  error.value = ''
  try {
    const payload = { ...form.value, contract_id: Number(form.value.contract_id), station_id: Number(form.value.station_id) }
    const { data } = await api.post('/inspections/start', payload)
    router.push(`/inspections/${data.id}?contract_id=${payload.contract_id}&station_id=${payload.station_id}`)
  } catch(e){ error.value = e.response?.data?.detail || 'Unable to start inspection' }
}
</script>
<style scoped>.mini{background:#f8fafc}.error{color:#dc2626;font-weight:700}</style>
