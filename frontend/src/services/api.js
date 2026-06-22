import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1'
})

const refreshClient = axios.create({
  baseURL: '/api/v1'
})

let refreshPromise = null

function redirectToLogin() {
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.assign('/login')
  }
}

function isAuthRefreshSkipped(config = {}) {
  const url = String(config.url || '')
  return Boolean(config.skipAuthRefresh)
    || url.includes('/auth/login')
    || url.includes('/auth/refresh')
    || url.includes('/auth/logout')
}

export function getAccessToken() {
  return localStorage.getItem('access_token')
}

export function getRefreshToken() {
  return localStorage.getItem('refresh_token')
}

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {}
    const status = error.response?.status

    if (status !== 401 || original._retry || isAuthRefreshSkipped(original)) {
      throw error
    }

    const refreshToken = getRefreshToken()
    if (!refreshToken) {
      clearTokens()
      redirectToLogin()
      throw error
    }

    original._retry = true

    try {
      await refreshTokens()
      original.headers = original.headers || {}
      original.headers.Authorization = `Bearer ${getAccessToken()}`
      return api(original)
    } catch (refreshError) {
      clearTokens()
      redirectToLogin()
      throw refreshError
    }
  }
)

export function setTokens(data) {
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
}

export function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export async function refreshTokens() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) throw new Error('Refresh token is missing')

  if (!refreshPromise) {
    refreshPromise = refreshClient
      .post('/auth/refresh', { refresh_token: refreshToken })
      .then(({ data }) => {
        setTokens(data)
        return data
      })
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

export async function revokeRefreshToken(refreshToken) {
  if (!refreshToken) return
  await refreshClient.post('/auth/logout', { refresh_token: refreshToken })
}

export async function getPdfBlobUrl(url, params = {}) {
  const { data } = await api.get(url, { params, responseType: 'blob' })
  const blob = new Blob([data], { type: 'application/pdf' })
  return window.URL.createObjectURL(blob)
}

export async function downloadBlob(url, params, filename) {
  const blobUrl = await getPdfBlobUrl(url, params || {})
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(blobUrl)
}
