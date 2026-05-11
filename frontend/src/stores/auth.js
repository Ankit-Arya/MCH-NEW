import { defineStore } from 'pinia'
import { api, setTokens, clearTokens } from '../services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null, loading: false }),
  getters: { isLoggedIn: (state) => !!state.user },
  actions: {
    async login(username, password) {
      this.loading = true
      try {
        const { data } = await api.post('/auth/login', { username, password })
        setTokens(data)
        await this.fetchMe()
      } finally {
        this.loading = false
      }
    },
    async fetchMe() {
      const { data } = await api.get('/auth/me')
      this.user = data
    },
    logout() {
      clearTokens()
      this.user = null
    }
  }
})
