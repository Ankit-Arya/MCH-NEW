import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import InspectionStartView from '../views/InspectionStartView.vue'
import InspectionFormView from '../views/InspectionFormView.vue'
import ActionRequiredView from '../views/ActionRequiredView.vue'
import ReviewQueueView from '../views/ReviewQueueView.vue'
import KpiDashboardView from '../views/KpiDashboardView.vue'
import MasterDataView from '../views/MasterDataView.vue'
import ReportsView from '../views/ReportsView.vue'
import AccessControlView from '../views/AccessControlView.vue'
import AdminSqlToolView from '../views/AdminSqlToolView.vue'

const routes = [
  { path: '/login', component: LoginView },
  { path: '/', component: DashboardView, meta: { requiresAuth: true } },
  { path: '/inspections/start', component: InspectionStartView, meta: { requiresAuth: true } },
  { path: '/inspections/action-required', component: ActionRequiredView, meta: { requiresAuth: true } },
  { path: '/inspections/:id', component: InspectionFormView, meta: { requiresAuth: true } },
  { path: '/reports', component: ReportsView, meta: { requiresAuth: true } },
  { path: '/reviews', component: ReviewQueueView, meta: { requiresAuth: true } },
  { path: '/kpi', component: KpiDashboardView, meta: { requiresAuth: true } },
  { path: '/master', component: MasterDataView, meta: { requiresAuth: true } },
  { path: '/access-control', component: AccessControlView, meta: { requiresAuth: true } },
  { path: '/admin/sql', component: AdminSqlToolView, meta: { requiresAuth: true, roles: ['SUPER_ADMIN', 'HK_CELL_ADMIN'] } }
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

  if (to.meta.roles?.length && !to.meta.roles.includes(auth.user?.role)) {
    return '/'
  }
})

export default router
