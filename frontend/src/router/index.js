
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import InspectionStartView from '../views/InspectionStartView.vue'
import InspectionFormView from '../views/InspectionFormView.vue'
import ReviewQueueView from '../views/ReviewQueueView.vue'
import KpiDashboardView from '../views/KpiDashboardView.vue'
import MasterDataView from '../views/MasterDataView.vue'
import ReportsView from '../views/ReportsView.vue'

const routes = [
  { path: '/login', component: LoginView },
  { path: '/', component: DashboardView, meta: { requiresAuth: true } },
  { path: '/inspections/start', component: InspectionStartView, meta: { requiresAuth: true } },
  { path: '/inspections/:id', component: InspectionFormView, meta: { requiresAuth: true } },
  { path: '/reports', component: ReportsView, meta: { requiresAuth: true } },
  { path: '/reviews', component: ReviewQueueView, meta: { requiresAuth: true } },
  { path: '/kpi', component: KpiDashboardView, meta: { requiresAuth: true } },
  { path: '/master', component: MasterDataView, meta: { requiresAuth: true } }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.user) {
    const token = localStorage.getItem('access_token')
    if (token) {
      try { await auth.fetchMe() } catch { return '/login' }
    } else {
      return '/login'
    }
  }
})

export default router
