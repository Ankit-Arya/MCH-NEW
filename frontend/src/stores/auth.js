import { defineStore } from 'pinia'
import { api, clearTokens, getRefreshToken, revokeRefreshToken, setTokens } from '../services/api'

const LOGIN_SESSION_KEY = 'mch-login-session-id'

function newLoginSessionId() {
  return `login-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function startLoginSession() {
  if (typeof sessionStorage === 'undefined') return
  sessionStorage.setItem(LOGIN_SESSION_KEY, newLoginSessionId())
}

function ensureLoginSession() {
  if (typeof sessionStorage === 'undefined') return
  if (!sessionStorage.getItem(LOGIN_SESSION_KEY)) {
    sessionStorage.setItem(LOGIN_SESSION_KEY, newLoginSessionId())
  }
}

function clearLoginSession() {
  if (typeof sessionStorage === 'undefined') return
  sessionStorage.removeItem(LOGIN_SESSION_KEY)
}

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null, loading: false }),
  getters: { isLoggedIn: (state) => !!state.user },
  actions: {
    async login(username, password) {
      this.loading = true
      try {
        const { data } = await api.post('/auth/login', { username, password })
        setTokens(data)
        startLoginSession()
        await this.fetchMe()
      } finally {
        this.loading = false
      }
    },
    async fetchMe() {
      ensureLoginSession()
      const { data } = await api.get('/auth/me')
      this.user = data
    },
    logout() {
      const refreshToken = getRefreshToken()
      clearTokens()
      clearLoginSession()
      this.user = null
      if (refreshToken) {
        revokeRefreshToken(refreshToken).catch(() => {})
      }
    }
  }
})
