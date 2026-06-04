import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Cache-Control': 'no-cache' }
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function setTokens(data) {
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
}

export function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export async function downloadBlob(url, params, filename) {
  const { data } = await api.get(url, { params, responseType: 'blob' })
  const blobUrl = window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' }))
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(blobUrl)
}


export function withTimestamp(params = {}) {
  return { ...params, _ts: Date.now() }
}
