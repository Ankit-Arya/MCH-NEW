
<template>
  <div class="page shell">
    <aside class="sidebar">
      <div class="brand-card">
        <img src="../assets/dmrc-logo.svg" alt="DMRC" class="brand-logo" />
        <div>
          <strong>MCH KPI-6</strong>
          <span>Cleanliness Inspection</span>
        </div>
      </div>
      <nav>
        <RouterLink to="/">Dashboard</RouterLink>
        <RouterLink to="/inspections/start">Start Inspection</RouterLink>
        <RouterLink to="/reports">Reports & PDFs</RouterLink>
        <RouterLink to="/reviews">Review Queue</RouterLink>
        <RouterLink to="/kpi">KPI & Penalty</RouterLink>
        <RouterLink to="/master">Master Data</RouterLink>
      </nav>
      <div class="sidebar-note">
        <strong>Demo users</strong>
        <span>admin/admin123 · sm01/sm123 · lm01/lm123 · dgm01/dgm123 · gm01/gm123</span>
      </div>
    </aside>
    <main class="content">
      <header class="topbar">
        <div class="topbar-title">
          <span class="mini-logo"><img src="../assets/dmrc-logo.svg" alt="DMRC" /></span>
          <div>
            <strong>{{ auth.user?.name || 'User' }}</strong>
            <span class="badge blue">{{ auth.user?.role || 'ROLE' }}</span>
          </div>
        </div>
        <button class="btn btn-muted" @click="logout">Logout</button>
      </header>
      <slot />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
const router = useRouter()
const auth = useAuthStore()
function logout() { auth.logout(); router.push('/login') }
</script>

<style scoped>
.shell { display:flex; }
.sidebar {
  width: 292px;
  color:white;
  padding:22px;
  min-height:100vh;
  position: sticky;
  top:0;
  background:
    radial-gradient(circle at 0 0, rgba(215,25,32,.28), transparent 28%),
    linear-gradient(180deg, #061a44 0%, #092b6f 52%, #081f50 100%);
  box-shadow: 12px 0 32px rgba(8,31,80,.18);
}
.brand-card { display:flex; gap:12px; align-items:center; background: rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.14); border-radius:20px; padding:12px; }
.brand-logo { width:112px; height:auto; border-radius:14px; }
.brand-card strong { display:block; font-size:16px; }
.brand-card span { display:block; color:#cbd5e1; font-size:12px; margin-top:3px; }
nav { display:grid; gap:9px; margin-top:28px; }
nav a { padding:13px 14px; border-radius:14px; color:#dbeafe; font-weight:800; }
nav a.router-link-active, nav a:hover { background: rgba(255,255,255,.13); color:white; }
.sidebar-note { margin-top:28px; padding:14px; border-radius:18px; background:rgba(255,255,255,.10); color:#dbeafe; font-size:12px; line-height:1.5; }
.sidebar-note strong { display:block; color:white; margin-bottom:5px; }
.content { flex:1; padding:26px; min-width:0; }
.topbar { display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:rgba(255,255,255,.75); border:1px solid rgba(219,227,240,.8); border-radius:22px; padding:12px 14px; backdrop-filter: blur(8px); }
.topbar-title { display:flex; align-items:center; gap:12px; }
.topbar-title strong { display:block; margin-bottom:4px; }
.mini-logo { display:none; }
.mini-logo img { width:92px; }
@media (max-width: 820px) {
  .shell { display:block; }
  .sidebar { width:100%; min-height:auto; position:relative; border-radius:0 0 26px 26px; }
  .brand-card { display:none; }
  nav { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top:0; }
  .sidebar-note { display:none; }
  .content { padding:14px; }
  .mini-logo { display:inline-flex; }
}
</style>
