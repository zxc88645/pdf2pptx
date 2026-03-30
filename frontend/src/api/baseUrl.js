const STORAGE_KEY = 'pdf2pptx.apiBaseUrl'

export function normalizeApiBaseUrl(input) {
  const raw = String(input ?? '').trim()
  if (!raw) return ''
  return raw.replace(/\/+$/, '')
}

export function getApiBaseUrl() {
  const fromStorage = normalizeApiBaseUrl(localStorage.getItem(STORAGE_KEY))
  if (fromStorage) return fromStorage
  return normalizeApiBaseUrl(import.meta.env.VITE_API_BASE || '')
}

export function getStoredApiBaseUrl() {
  return normalizeApiBaseUrl(localStorage.getItem(STORAGE_KEY))
}

export function getEnvApiBaseUrl() {
  return normalizeApiBaseUrl(import.meta.env.VITE_API_BASE || '')
}

export function setApiBaseUrl(nextBaseUrl) {
  const normalized = normalizeApiBaseUrl(nextBaseUrl)
  if (!normalized) {
    localStorage.removeItem(STORAGE_KEY)
    return ''
  }
  localStorage.setItem(STORAGE_KEY, normalized)
  return normalized
}

export function clearApiBaseUrl() {
  localStorage.removeItem(STORAGE_KEY)
}

export function apiUrl(path) {
  const baseURL = getApiBaseUrl()
  const p = String(path || '')
  if (!baseURL) return p
  if (!p) return baseURL
  return p.startsWith('/') ? `${baseURL}${p}` : `${baseURL}/${p}`
}

