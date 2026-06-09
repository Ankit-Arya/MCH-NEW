<template>
  <div class="page shell" :class="{ 'nav-open': mobileMenuOpen }">
    <div
      v-if="mobileMenuOpen"
      class="mobile-backdrop"
      aria-hidden="true"
      @click="closeMobileMenu"
    ></div>

    <aside class="sidebar" :class="{ 'menu-open': mobileMenuOpen }" aria-label="Application navigation">
      <div class="brand-card">
        <button
          class="mobile-menu-btn"
          :class="{ 'is-open': mobileMenuOpen }"
          type="button"
          :aria-label="mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'"
          :aria-expanded="mobileMenuOpen ? 'true' : 'false'"
          aria-controls="mobile-navigation-panel"
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

        <button class="mobile-logout-btn" type="button" @click="logout">
          Logout
        </button>
      </div>

      <nav
        id="mobile-navigation-panel"
        class="main-nav"
        aria-label="Main navigation"
        :aria-hidden="isMobileMenuHidden"
      >
        <div class="drawer-user-card">
          <small>Logged in as</small>
          <strong>{{ auth.user?.name || 'User' }}</strong>
          <span>{{ auth.user?.role || 'ROLE' }}</span>
        </div>

        <RouterLink to="/" @click="closeMobileMenu">Dashboard</RouterLink>
        <RouterLink to="/inspections/start" @click="closeMobileMenu">Start Inspection</RouterLink>
        <RouterLink to="/reports" @click="closeMobileMenu">Reports & PDFs</RouterLink>
        <RouterLink to="/reviews" @click="closeMobileMenu">Review Queue</RouterLink>
        <RouterLink to="/kpi" @click="closeMobileMenu">KPI & Penalty</RouterLink>
        <RouterLink to="/master" @click="closeMobileMenu">Master Data</RouterLink>
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

        <button class="btn btn-muted logout-btn" type="button" @click="logout">
          Logout
        </button>
      </header>

      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const mobileMenuOpen = ref(false)

const isMobileMenuHidden = computed(() => (mobileMenuOpen.value ? 'false' : 'true'))

let lockedScrollY = 0
let previousBodyPosition = ''
let previousBodyTop = ''
let previousBodyLeft = ''
let previousBodyRight = ''
let previousBodyWidth = ''
let previousBodyOverflow = ''
let previousHtmlOverscroll = ''

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

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

function closeMobileMenu() {
  mobileMenuOpen.value = false
}

function logout() {
  closeMobileMenu()
  auth.logout()
  router.push('/login')
}

function handleKeydown(event) {
  if (event.key === 'Escape') closeMobileMenu()
}

function handleResize() {
  if (window.innerWidth > 820) closeMobileMenu()
}

watch(
  () => router.currentRoute.value.fullPath,
  () => closeMobileMenu()
)

watch(mobileMenuOpen, (isOpen) => {
  if (isOpen) lockPageScroll()
  else unlockPageScroll()
})

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  unlockPageScroll()
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.shell {
  display: block;
  min-height: 100vh;
}

.sidebar {
  width: 292px;
  color: white;
  padding: 22px;
  min-height: 100vh;
  height: 100dvh;
  position: fixed;
  inset: 0 auto 0 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  background:
    radial-gradient(circle at 0 0, rgba(215,25,32,.28), transparent 28%),
    linear-gradient(180deg, #061a44 0%, #092b6f 52%, #081f50 100%);
  box-shadow: 12px 0 32px rgba(8,31,80,.18);
  z-index: 40;
}

.brand-card {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  background: rgba(255,255,255,.10);
  border: 1px solid rgba(255,255,255,.14);
  border-radius: 20px;
  padding: 12px;
  position: relative;
  z-index: 2;
}

.brand-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  color: white;
  text-decoration: none;
}

.brand-logo {
  width: 112px;
  height: auto;
  border-radius: 14px;
  flex: 0 0 auto;
}

.brand-copy {
  min-width: 0;
}

.brand-card strong {
  display: block;
  font-size: 16px;
  line-height: 1.15;
}

.brand-copy > span {
  display: block;
  color: #cbd5e1;
  font-size: 12px;
  margin-top: 3px;
}

.main-nav {
  display: grid;
  gap: 9px;
  margin-top: 28px;
}

.main-nav a {
  padding: 13px 14px;
  border-radius: 14px;
  color: #dbeafe;
  font-weight: 800;
  text-decoration: none;
}

.main-nav a.router-link-active,
.main-nav a:hover {
  background: rgba(255,255,255,.13);
  color: white;
}

.drawer-user-card {
  display: none;
}

.sidebar-note {
  margin-top: 28px;
  padding: 14px;
  border-radius: 18px;
  background: rgba(255,255,255,.10);
  color: #dbeafe;
  font-size: 12px;
  line-height: 1.5;
}

.sidebar-note strong {
  display: block;
  color: white;
  margin-bottom: 5px;
}

.content {
  min-width: 0;
  margin-left: 292px;
  padding: 26px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  background: rgba(255,255,255,.75);
  border: 1px solid rgba(219,227,240,.8);
  border-radius: 22px;
  padding: 12px 14px;
  backdrop-filter: blur(8px);
}

.topbar-title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1 1 auto;
}

.user-copy {
  min-width: 0;
}

.topbar-title strong {
  display: block;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 46vw;
}

.logout-btn {
  margin-left: auto;
  flex: 0 0 auto;
  white-space: nowrap;
}

.mini-logo {
  display: none;
}

.mini-logo img {
  width: 92px;
}

.mobile-menu-btn,
.mobile-logout-btn,
.mobile-backdrop {
  display: none;
}

.mobile-menu-btn {
  width: 44px;
  height: 44px;
  border: 1px solid rgba(255,255,255,.22);
  border-radius: 14px;
  background: rgba(255,255,255,.12);
  color: white;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 5px;
  padding: 0;
  flex: 0 0 auto;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.mobile-menu-btn span {
  display: block;
  width: 22px;
  height: 3px;
  border-radius: 999px;
  background: white;
  transition: transform .18s ease, opacity .18s ease;
}

.mobile-menu-btn.is-open span:nth-child(1) {
  transform: translateY(8px) rotate(45deg);
}

.mobile-menu-btn.is-open span:nth-child(2) {
  opacity: 0;
}

.mobile-menu-btn.is-open span:nth-child(3) {
  transform: translateY(-8px) rotate(-45deg);
}

@media (max-width: 820px) {
  .shell {
    display: block;
  }

  .sidebar {
    --safe-top: env(safe-area-inset-top, 0px);
    --header-x: 10px;
    --header-top: 8px;
    --header-height: 58px;
    --header-total: calc(var(--safe-top) + var(--header-top) + var(--header-height) + 10px);
    width: 100%;
    min-height: 0;
    height: var(--header-total);
    max-height: 100dvh;
    position: fixed;
    inset: 0 0 auto 0;
    z-index: 1000;
    padding: calc(var(--safe-top) + var(--header-top)) var(--header-x) 10px;
    overflow: hidden;
    border-radius: 0 0 24px 24px;
    box-shadow: 0 12px 30px rgba(8,31,80,.20);
    transition: height .22s ease, border-radius .22s ease, box-shadow .22s ease;
  }

  .sidebar.menu-open {
    height: min(100dvh, 594px);
    border-radius: 0 0 26px 26px;
    box-shadow: 0 26px 72px rgba(2,6,23,.36);
  }

  .brand-card {
    min-height: var(--header-height);
    padding: 8px 10px;
    border-radius: 18px;
    gap: 8px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.14);
  }

  .brand-left {
    flex: 1 1 auto;
    min-width: 0;
    justify-content: flex-start;
  }

  .brand-logo {
    width: 58px;
    border-radius: 10px;
  }

  .brand-card strong {
    font-size: 15px;
    white-space: nowrap;
  }

  .brand-copy > span {
    display: none;
  }

  .mobile-menu-btn {
    display: inline-flex;
  }

  .brand-card .mobile-menu-btn span {
    display: block !important;
    width: 22px;
    height: 3px;
    min-height: 3px;
    border-radius: 999px;
    background: #ffffff !important;
    box-shadow: 0 1px 2px rgba(0,0,0,.18);
    opacity: 1;
    visibility: visible;
  }

  .mobile-logout-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 38px;
    padding: 0 12px;
    border: 1px solid rgba(255,255,255,.24);
    border-radius: 999px;
    background: rgba(255,255,255,.16);
    color: white;
    font-size: 13px;
    font-weight: 900;
    white-space: nowrap;
    flex: 0 0 auto;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }

  .mobile-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 999;
    background: rgba(15,23,42,.38);
    backdrop-filter: blur(3px);
  }

  .main-nav {
    margin: 10px 0 0;
    padding: 0 0 14px;
    grid-template-columns: 1fr;
    gap: 8px;
    max-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transform: translateY(-6px);
    transition: max-height .22s ease, opacity .18s ease, transform .18s ease, visibility .18s ease;
  }

  .menu-open .main-nav {
    max-height: calc(100dvh - var(--header-total) - 12px);
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
    transform: translateY(0);
  }

  .drawer-user-card {
    display: block;
    padding: 12px 14px;
    border-radius: 16px;
    background: rgba(255,255,255,.11);
    border: 1px solid rgba(255,255,255,.12);
    margin-bottom: 6px;
    color: white;
  }

  .drawer-user-card small {
    display: block;
    color: #bfdbfe;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-bottom: 4px;
  }

  .drawer-user-card strong {
    display: block;
    font-size: 14px;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .drawer-user-card span {
    display: inline-flex;
    margin-top: 6px;
    padding: 4px 8px;
    border-radius: 999px;
    background: rgba(255,255,255,.16);
    color: white;
    font-size: 11px;
    font-weight: 900;
  }

  .main-nav a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 48px;
    padding: 13px 14px;
    border-radius: 14px;
    background: rgba(255,255,255,.075);
  }

  .main-nav a::after {
    content: '›';
    opacity: .72;
    font-size: 20px;
    line-height: 1;
  }

  .sidebar-note {
    display: none;
  }

  .content {
    margin-left: 0;
    padding: calc(var(--header-total, 86px) + 14px) 14px 14px;
  }

  .topbar {
    display: none;
  }
}

@media (max-width: 420px) {
  .sidebar {
    --header-x: 10px;
    --header-top: 8px;
    --header-height: 54px;
  }

  .brand-card {
    padding: 7px 8px;
  }

  .mobile-menu-btn {
    width: 42px;
    height: 42px;
    border-radius: 13px;
  }

  .brand-logo {
    width: 52px;
  }

  .brand-card strong {
    font-size: 14px;
  }

  .mobile-logout-btn {
    min-height: 36px;
    padding: 0 10px;
    font-size: 12px;
  }
}

@media (max-width: 360px) {
  .brand-logo {
    width: 46px;
  }

  .brand-card strong {
    font-size: 13px;
  }

  .mobile-logout-btn {
    padding: 0 8px;
  }
}
</style>
