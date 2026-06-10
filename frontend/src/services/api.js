import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1'
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
