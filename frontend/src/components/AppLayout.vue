<template>
  <div class="page shell" :class="{ 'nav-open': mobileMenuOpen }">
    <div v-if="mobileMenuOpen" class="mobile-backdrop" aria-hidden="true" @click="closeMobileMenu"></div>

    <aside class="sidebar" :class="{ 'menu-open': mobileMenuOpen }" aria-label="Application navigation">
      <div class="brand-card">
        <button
          class="mobile-menu-btn"
          :class="{ 'is-open': mobileMenuOpen }"
          type="button"
          :aria-label="mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'"
          :aria-expanded="mobileMenuOpen ? 'true' : 'false'"
          @click="toggleMobileMenu"
        >
          <span aria-hidden="true"></span>
          <span aria-hidden="true"></span>
          <span aria-hidden="true"></span>
        </button>

        <RouterLink class="brand-left" to="/" @click="closeMobileMenu">
          <img src="../assets/dmrc-logo.svg" alt="DMRC" class="brand-logo" />
          <div class="brand-copy">
            <strong>MCH KPI-6</strong>
            <span>Cleanliness Inspection</span>
          </div>
        </RouterLink>

        <button class="mobile-logout-btn" type="button" @click="logout">Logout</button>
      </div>

      <nav class="main-nav" aria-label="Main navigation" :aria-hidden="isMobileMenuHidden">
        <div class="drawer-user-card">
          <small>Logged in as</small>
          <strong>{{ auth.user?.name || 'User' }}</strong>
          <span>{{ auth.user?.role || 'ROLE' }}</span>
        </div>

        <RouterLink to="/" @click="closeMobileMenu">Dashboard</RouterLink>
        <RouterLink to="/inspections/start" @click="closeMobileMenu">Start Inspection</RouterLink>
        <RouterLink to="/inspections/action-required" @click="closeMobileMenu">
          Action Required
          <span v-if="actionRequiredNotice.count" class="nav-review-pill action-pill">{{ actionRequiredNotice.count }}</span>
        </RouterLink>
        <RouterLink to="/reports" @click="closeMobileMenu">Reports & PDFs</RouterLink>
        <RouterLink to="/reviews" @click="closeMobileMenu">
          Review Queue
          <span v-if="pendingReviewNotice.count" class="nav-review-pill">{{ pendingReviewNotice.count }}</span>
        </RouterLink>
        <RouterLink to="/kpi" @click="closeMobileMenu">KPI & Penalty</RouterLink>
        <RouterLink to="/master" @click="closeMobileMenu">Master Data</RouterLink>
        <RouterLink to="/access-control" @click="closeMobileMenu">Access Control</RouterLink>
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
          <div class="user-copy">
            <strong>{{ auth.user?.name || 'User' }}</strong>
            <span class="badge blue">{{ auth.user?.role || 'ROLE' }}</span>
          </div>
        </div>

        <button
          v-if="actionRequiredNotice.count"
          class="review-alert-chip action-alert-chip"
          type="button"
          @click="openActionRequiredNotice"
          :title="`${actionRequiredNotice.count} action required item(s)`"
        >
          <span class="review-alert-dot action-dot" aria-hidden="true"></span>
          {{ actionRequiredNotice.count }} action required
        </button>

        <button
          v-if="pendingReviewNotice.count"
          class="review-alert-chip"
          type="button"
          @click="openPendingReviewNotice"
          :title="`${pendingReviewNotice.count} pending review(s)`"
        >
          <span class="review-alert-dot" aria-hidden="true"></span>
          {{ pendingReviewNotice.count }} pending review{{ pendingReviewNotice.count === 1 ? '' : 's' }}
        </button>

        <button class="btn btn-muted logout-btn" type="button" @click="logout">Logout</button>
      </header>

      <slot />
    </main>

    <div v-if="actionRequiredNotice.open" class="review-notice-backdrop" role="presentation" @click.self="dismissActionRequiredNotice">
      <section class="review-notice-modal action-notice-modal" role="dialog" aria-modal="true" aria-labelledby="action-required-title">
        <button class="review-notice-close" type="button" aria-label="Close action required notification" @click="dismissActionRequiredNotice">×</button>
        <div class="review-notice-icon action-icon" aria-hidden="true">!</div>
        <p class="review-notice-kicker">Inspection action required</p>
        <h2 id="action-required-title">{{ actionRequiredNotice.count }} draft/returned inspection{{ actionRequiredNotice.count === 1 ? '' : 's' }} need your action</h2>
        <p class="review-notice-text">
          Draft inspections and returned-for-clarification inspections are waiting for you to complete, correct, and resubmit.
        </p>
        <div class="review-notice-meta">
          <span>Break-up</span>
          <strong>{{ actionRequiredNotice.draft }} draft · {{ actionRequiredNotice.returned }} returned</strong>
          <small>{{ auth.user?.name || 'User' }}</small>
        </div>
        <div class="review-notice-actions">
          <button class="btn btn-primary" type="button" @click="goToActionRequired">Open Action Required</button>
          <button class="btn btn-muted" type="button" @click="dismissActionRequiredNotice">Remind me later</button>
        </div>
      </section>
    </div>

    <div v-if="pendingReviewNotice.open" class="review-notice-backdrop" role="presentation" @click.self="dismissPendingReviewNotice">
      <section class="review-notice-modal" role="dialog" aria-modal="true" aria-labelledby="pending-review-title">
        <button class="review-notice-close" type="button" aria-label="Close pending review notification" @click="dismissPendingReviewNotice">×</button>
        <div class="review-notice-icon" aria-hidden="true">!</div>
        <p class="review-notice-kicker">Review attention required</p>
        <h2 id="pending-review-title">{{ pendingReviewNotice.count }} inspection review{{ pendingReviewNotice.count === 1 ? '' : 's' }} pending at your level</h2>
        <p class="review-notice-text">
          These inspections are waiting for action from {{ reviewerRoleLabel }}. Open the Review Queue to view PDFs, tracker status and approve or recommend as applicable.
        </p>
        <div class="review-notice-meta">
          <span>Logged in as</span>
          <strong>{{ auth.user?.name || 'User' }}</strong>
          <small>{{ reviewerRoleLabel }}</small>
        </div>
        <div class="review-notice-actions">
          <button class="btn btn-primary" type="button" @click="goToReviews">Open Review Queue</button>
          <button class="btn btn-muted" type="button" @click="dismissPendingReviewNotice">Remind me later</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api } from '../services/api'

const router = useRouter()
const auth = useAuthStore()
const mobileMenuOpen = ref(false)
const isMobileMenuHidden = computed(() => (mobileMenuOpen.value ? 'false' : 'true'))
const reviewerRoles = new Set(['AM_MGR_LINE', 'AM_MGR_HK', 'DGM_LINE', 'DGM_HK', 'GM_OPS'])

const pendingReviewNotice = reactive({ open: false, count: 0, checkedKey: '', loading: false })
const actionRequiredNotice = reactive({ open: false, count: 0, draft: 0, returned: 0, checkedKey: '', loading: false })
const reviewerRoleLabel = computed(() => roleLabel(auth.user?.role))

let lockedScrollY = 0
let previousBodyPosition = ''
let previousBodyTop = ''
let previousBodyLeft = ''
let previousBodyRight = ''
let previousBodyWidth = ''
let previousBodyOverflow = ''
let previousHtmlOverscroll = ''

function roleLabel(role) {
  const labels = {
    SUPER_ADMIN: 'Super Admin',
    HK_CELL_ADMIN: 'HK Cell Admin',
    GM_OPS: 'GM/Ops',
    DGM_LINE: 'DGM Line',
    DGM_HK: 'DGM HK',
    AM_MGR_LINE: 'Line Manager',
    AM_MGR_HK: 'HK Manager',
    STATION_MANAGER: 'Station Manager',
    EIT_MEMBER: 'External Inspection Team',
    AUDITOR: 'Auditor'
  }
  return labels[role] || role || 'Reviewer'
}

function lockPageScroll() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  lockedScrollY = window.scrollY || document.documentElement.scrollTop || 0
  previousBodyPosition = document.body.style.position
  previousBodyTop = document.body.style.top
  previousBodyLeft = document.body.style.left
  previousBodyRight = document.body.style.right
  previousBodyWidth = document.body.style.width
  previousBodyOverflow = document.body.style.overflow
  previousHtmlOverscroll = document.documentElement.style.overscrollBehavior
  document.body.style.position = 'fixed'
  document.body.style.top = `-${lockedScrollY}px`
  document.body.style.left = '0'
  document.body.style.right = '0'
  document.body.style.width = '100%'
  document.body.style.overflow = 'hidden'
  document.documentElement.style.overscrollBehavior = 'none'
}

function unlockPageScroll() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  document.body.style.position = previousBodyPosition
  document.body.style.top = previousBodyTop
  document.body.style.left = previousBodyLeft
  document.body.style.right = previousBodyRight
  document.body.style.width = previousBodyWidth
  document.body.style.overflow = previousBodyOverflow
  document.documentElement.style.overscrollBehavior = previousHtmlOverscroll
  window.scrollTo(0, lockedScrollY)
}

function toggleMobileMenu() { mobileMenuOpen.value = !mobileMenuOpen.value }
function closeMobileMenu() { mobileMenuOpen.value = false }
function logout() {
  closeMobileMenu()
  pendingReviewNotice.open = false
  pendingReviewNotice.count = 0
  actionRequiredNotice.open = false
  actionRequiredNotice.count = 0
  auth.logout()
  router.push('/login')
}
function handleKeydown(event) {
  if (event.key !== 'Escape') return
  if (actionRequiredNotice.open) { dismissActionRequiredNotice(); return }
  if (pendingReviewNotice.open) { dismissPendingReviewNotice(); return }
  closeMobileMenu()
}
function handleResize() { if (window.innerWidth > 820) closeMobileMenu() }

const LOGIN_SESSION_KEY = 'mch-login-session-id'

function ensureLoginSessionId() {
  if (typeof sessionStorage === 'undefined') return 'browser-session'
  let loginSessionId = sessionStorage.getItem(LOGIN_SESSION_KEY)
  if (!loginSessionId) {
    loginSessionId = `restored-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
    sessionStorage.setItem(LOGIN_SESSION_KEY, loginSessionId)
  }
  return loginSessionId
}

function sessionKey(prefix, user) {
  if (!user?.id && !user?.username && !user?.role) return ''
  const loginSessionId = ensureLoginSessionId()
  return `${prefix}:${loginSessionId}:${user.id || user.username || 'user'}:${user.role}`
}
function pendingReviewSessionKey(user) { return sessionKey('mch-pending-review-popup', user) }
function actionRequiredSessionKey(user) { return sessionKey('mch-action-required-popup', user) }
function shouldCheckPendingReviews(user) { return Boolean(user?.role && reviewerRoles.has(user.role)) }
function shouldCheckActionRequired(user) { return Boolean(user?.role && !reviewerRoles.has(user.role)) || ['SUPER_ADMIN', 'HK_CELL_ADMIN'].includes(user?.role) }
function markNoticeChecked(key) { if (key && typeof sessionStorage !== 'undefined') sessionStorage.setItem(key, 'checked') }
function wasNoticeChecked(key) { return Boolean(key && typeof sessionStorage !== 'undefined' && sessionStorage.getItem(key) === 'checked') }

function openPendingReviewNotice() { if (pendingReviewNotice.count > 0) pendingReviewNotice.open = true }
function dismissPendingReviewNotice() { pendingReviewNotice.open = false; markNoticeChecked(pendingReviewNotice.checkedKey) }
function openActionRequiredNotice() { if (actionRequiredNotice.count > 0) actionRequiredNotice.open = true }
function dismissActionRequiredNotice() { actionRequiredNotice.open = false; markNoticeChecked(actionRequiredNotice.checkedKey) }
async function goToReviews() { dismissPendingReviewNotice(); closeMobileMenu(); await router.push('/reviews') }
async function goToActionRequired() { dismissActionRequiredNotice(); closeMobileMenu(); await router.push('/inspections/action-required') }

async function checkPendingReviewsForUser(user) {
  if (!shouldCheckPendingReviews(user) || pendingReviewNotice.loading) return
  const key = pendingReviewSessionKey(user)
  if (!key || wasNoticeChecked(key)) return
  pendingReviewNotice.loading = true
  pendingReviewNotice.checkedKey = key
  try {
    const { data } = await api.get('/reviews/pending', { params: { page: 1, size: 1 } })
    const count = Number(data?.total || 0)
    pendingReviewNotice.count = count
    if (count > 0 && router.currentRoute.value.path !== '/reviews') pendingReviewNotice.open = true
  } catch {
    pendingReviewNotice.count = 0
  } finally { pendingReviewNotice.loading = false }
}

async function checkActionRequiredForUser(user) {
  if (!shouldCheckActionRequired(user) || actionRequiredNotice.loading) return
  const key = actionRequiredSessionKey(user)
  if (!key || wasNoticeChecked(key)) return
  actionRequiredNotice.loading = true
  actionRequiredNotice.checkedKey = key
  try {
    const { data } = await api.get('/inspections/action-required', { params: { page: 1, size: 1 } })
    const count = Number(data?.total || 0)
    actionRequiredNotice.count = count
    actionRequiredNotice.draft = Number(data?.counts?.draft || 0)
    actionRequiredNotice.returned = Number(data?.counts?.returned || 0)
    if (count > 0 && router.currentRoute.value.path !== '/inspections/action-required') actionRequiredNotice.open = true
  } catch {
    actionRequiredNotice.count = 0
    actionRequiredNotice.draft = 0
    actionRequiredNotice.returned = 0
  } finally { actionRequiredNotice.loading = false }
}

watch(() => router.currentRoute.value.fullPath, () => closeMobileMenu())
watch(mobileMenuOpen, (isOpen) => { if (isOpen) lockPageScroll(); else unlockPageScroll() })
watch(() => auth.user, (user) => { checkPendingReviewsForUser(user); checkActionRequiredForUser(user) }, { immediate: true })

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', handleResize)
  checkPendingReviewsForUser(auth.user)
  checkActionRequiredForUser(auth.user)
})
onBeforeUnmount(() => {
  unlockPageScroll()
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.shell { display: block; min-height: 100vh; }
.sidebar { width: 292px; color: white; padding: 22px; min-height: 100vh; height: 100dvh; position: fixed; inset: 0 auto 0 0; overflow-y: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; background: radial-gradient(circle at 0 0, rgba(215,25,32,.28), transparent 28%), linear-gradient(180deg, #061a44 0%, #092b6f 52%, #081f50 100%); box-shadow: 12px 0 32px rgba(8,31,80,.18); z-index: 40; }
.brand-card { display: flex; gap: 12px; align-items: center; justify-content: space-between; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.14); border-radius: 20px; padding: 12px; position: relative; z-index: 2; }
.brand-left { display: flex; align-items: center; gap: 12px; min-width: 0; color: white; text-decoration: none; }
.brand-logo { width: 112px; height: auto; border-radius: 14px; flex: 0 0 auto; }
.brand-copy { min-width: 0; }
.brand-card strong { display: block; font-size: 16px; line-height: 1.15; }
.brand-copy > span { display: block; color: #cbd5e1; font-size: 12px; margin-top: 3px; }
.main-nav { display: grid; gap: 9px; margin-top: 28px; }
.main-nav a { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 13px 14px; border-radius: 14px; color: #dbeafe; font-weight: 800; text-decoration: none; }
.main-nav a.router-link-active, .main-nav a:hover { background: rgba(255,255,255,.13); color: white; }
.nav-review-pill { display: inline-flex; align-items: center; justify-content: center; min-width: 24px; height: 24px; padding: 0 7px; border-radius: 999px; background: #ef4444; color: white; font-size: 12px; font-weight: 900; box-shadow: 0 10px 22px rgba(239,68,68,.28); }
.action-pill { background: #f59e0b; box-shadow: 0 10px 22px rgba(245,158,11,.28); }
.drawer-user-card { display: none; }
.sidebar-note { margin-top: 28px; padding: 14px; border-radius: 18px; background: rgba(255,255,255,.10); color: #dbeafe; font-size: 12px; line-height: 1.5; }
.sidebar-note strong { display: block; color: white; margin-bottom: 5px; }
.content { min-width: 0; margin-left: 292px; padding: 26px; }
.topbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 20px; background: rgba(255,255,255,.75); border: 1px solid rgba(219,227,240,.8); border-radius: 22px; padding: 12px 14px; backdrop-filter: blur(8px); }
.topbar-title { display: flex; align-items: center; gap: 12px; min-width: 0; flex: 1 1 auto; }
.user-copy { min-width: 0; }
.topbar-title strong { display: block; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 46vw; }
.review-alert-chip { display: inline-flex; align-items: center; gap: 8px; border: 1px solid #fecaca; border-radius: 999px; background: #fff1f2; color: #991b1b; font-weight: 900; padding: 9px 12px; cursor: pointer; white-space: nowrap; box-shadow: 0 12px 24px rgba(153,27,27,.08); }
.review-alert-chip:hover { background: #ffe4e6; }
.action-alert-chip { border-color: #fde68a; background: #fffbeb; color: #92400e; }
.action-alert-chip:hover { background: #fef3c7; }
.review-alert-dot { width: 9px; height: 9px; border-radius: 999px; background: #ef4444; box-shadow: 0 0 0 5px rgba(239,68,68,.14); }
.action-dot { background: #f59e0b; box-shadow: 0 0 0 5px rgba(245,158,11,.16); }
.logout-btn { margin-left: auto; flex: 0 0 auto; white-space: nowrap; }
.mini-logo { display: none; }
.mini-logo img { width: 92px; }
.mobile-menu-btn, .mobile-logout-btn, .mobile-backdrop { display: none; }
.mobile-menu-btn { width: 44px; height: 44px; border: 1px solid rgba(255,255,255,.22); border-radius: 14px; background: rgba(255,255,255,.12); color: white; align-items: center; justify-content: center; flex-direction: column; gap: 5px; padding: 0; flex: 0 0 auto; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.mobile-menu-btn span { display: block; width: 22px; height: 3px; border-radius: 999px; background: white; transition: transform .18s ease, opacity .18s ease; }
.mobile-menu-btn.is-open span:nth-child(1) { transform: translateY(8px) rotate(45deg); }
.mobile-menu-btn.is-open span:nth-child(2) { opacity: 0; }
.mobile-menu-btn.is-open span:nth-child(3) { transform: translateY(-8px) rotate(-45deg); }
.review-notice-backdrop { position: fixed; inset: 0; z-index: 3000; display: grid; place-items: center; padding: 22px; background: rgba(15,23,42,.46); backdrop-filter: blur(4px); }
.review-notice-modal { width: min(520px, 100%); position: relative; border-radius: 28px; border: 1px solid rgba(219,227,240,.95); background: radial-gradient(circle at 0 0, rgba(239,68,68,.10), transparent 34%), linear-gradient(135deg, #ffffff 0%, #f8fbff 100%); box-shadow: 0 34px 90px rgba(15,23,42,.26); padding: 28px; text-align: center; }
.action-notice-modal { background: radial-gradient(circle at 0 0, rgba(245,158,11,.16), transparent 34%), linear-gradient(135deg, #ffffff 0%, #fffbeb 100%); }
.review-notice-close { position: absolute; top: 14px; right: 14px; width: 38px; height: 38px; border: 0; border-radius: 999px; background: #e2e8f0; color: #0f172a; font-size: 25px; line-height: 1; cursor: pointer; }
.review-notice-close:hover { background: #cbd5e1; }
.review-notice-icon { width: 70px; height: 70px; margin: 0 auto 14px; display: grid; place-items: center; border-radius: 22px; background: linear-gradient(135deg, #ef4444, #f97316); color: white; font-size: 38px; font-weight: 1000; box-shadow: 0 20px 40px rgba(239,68,68,.26); }
.action-icon { background: linear-gradient(135deg, #f59e0b, #ef4444); }
.review-notice-kicker { margin: 0 0 6px; color: #991b1b; font-size: 12px; font-weight: 1000; letter-spacing: .09em; text-transform: uppercase; }
.review-notice-modal h2 { margin: 0; color: #0f172a; font-size: clamp(22px, 3vw, 30px); line-height: 1.15; }
.review-notice-text { max-width: 440px; margin: 12px auto 0; color: #475569; line-height: 1.6; }
.review-notice-meta { display: grid; gap: 3px; margin: 18px auto 0; border: 1px solid #dbeafe; border-radius: 18px; background: #f8fbff; padding: 12px; color: #0f172a; }
.review-notice-meta span, .review-notice-meta small { color: #64748b; font-weight: 800; }
.review-notice-meta strong { font-size: 16px; }
.review-notice-actions { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin-top: 20px; }
@media (max-width: 820px) {
  .sidebar { --safe-top: env(safe-area-inset-top, 0px); --header-x: 10px; --header-top: 8px; --header-height: 58px; --header-total: calc(var(--safe-top) + var(--header-top) + var(--header-height) + 10px); width: 100%; min-height: 0; height: var(--header-total); max-height: 100dvh; position: fixed; inset: 0 0 auto 0; z-index: 1000; padding: calc(var(--safe-top) + var(--header-top)) var(--header-x) 10px; overflow: hidden; border-radius: 0 0 24px 24px; box-shadow: 0 12px 30px rgba(8,31,80,.20); transition: height .22s ease, border-radius .22s ease, box-shadow .22s ease; }
  .sidebar.menu-open { height: min(100dvh, 650px); border-radius: 0 0 26px 26px; box-shadow: 0 26px 72px rgba(2,6,23,.36); }
  .brand-card { min-height: var(--header-height); padding: 8px 10px; border-radius: 18px; gap: 8px; box-shadow: inset 0 1px 0 rgba(255,255,255,.14); }
  .brand-left { flex: 1 1 auto; min-width: 0; justify-content: flex-start; }
  .brand-logo { width: 58px; border-radius: 10px; }
  .brand-card strong { font-size: 15px; white-space: nowrap; }
  .brand-copy > span { display: none; }
  .mobile-menu-btn { display: inline-flex; }
  .mobile-logout-btn { display: inline-flex; align-items: center; justify-content: center; min-height: 38px; padding: 0 12px; border: 1px solid rgba(255,255,255,.24); border-radius: 999px; background: rgba(255,255,255,.16); color: white; font-size: 13px; font-weight: 900; white-space: nowrap; flex: 0 0 auto; cursor: pointer; -webkit-tap-highlight-color: transparent; }
  .mobile-backdrop { display: block; position: fixed; inset: 0; z-index: 999; background: rgba(15,23,42,.38); backdrop-filter: blur(3px); }
  .main-nav { margin: 10px 0 0; padding: 0 0 14px; grid-template-columns: 1fr; gap: 8px; max-height: 0; overflow-y: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; opacity: 0; visibility: hidden; pointer-events: none; transform: translateY(-6px); transition: max-height .22s ease, opacity .18s ease, transform .18s ease, visibility .18s ease; }
  .menu-open .main-nav { max-height: calc(100dvh - var(--header-total) - 12px); opacity: 1; visibility: visible; pointer-events: auto; transform: translateY(0); }
  .drawer-user-card { display: block; padding: 12px 14px; border-radius: 16px; background: rgba(255,255,255,.11); border: 1px solid rgba(255,255,255,.12); margin-bottom: 6px; color: white; }
  .drawer-user-card small { display: block; color: #bfdbfe; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px; }
  .drawer-user-card strong { display: block; font-size: 14px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .drawer-user-card span { display: inline-flex; margin-top: 6px; padding: 4px 8px; border-radius: 999px; background: rgba(255,255,255,.16); color: white; font-size: 11px; font-weight: 900; }
  .main-nav a { display: flex; align-items: center; justify-content: space-between; min-height: 48px; padding: 13px 14px; border-radius: 14px; background: rgba(255,255,255,.075); }
  .main-nav a::after { content: '›'; opacity: .72; font-size: 20px; line-height: 1; }
  .main-nav a:has(.nav-review-pill)::after { content: ''; }
  .sidebar-note { display: none; }
  .content { margin-left: 0; padding: calc(var(--header-total, 86px) + 14px) 14px 14px; }
  .topbar { display: none; }
  .review-notice-backdrop { padding: 16px; }
  .review-notice-modal { padding: 24px 18px; border-radius: 24px; }
  .review-notice-actions { display: grid; grid-template-columns: 1fr; }
}
@media (max-width: 420px) { .sidebar { --header-x: 10px; --header-top: 8px; --header-height: 54px; } .brand-card { padding: 7px 8px; } .mobile-menu-btn { width: 42px; height: 42px; border-radius: 13px; } .brand-logo { width: 52px; } .brand-card strong { font-size: 14px; } .mobile-logout-btn { min-height: 36px; padding: 0 10px; font-size: 12px; } }
@media (max-width: 360px) { .brand-logo { width: 46px; } .brand-card strong { font-size: 13px; } .mobile-logout-btn { padding: 0 8px; } }
</style>
