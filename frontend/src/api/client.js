import axios from 'axios'

import { getApiBaseUrl } from './baseUrl'

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

export function syncApiBaseUrl() {
  api.defaults.baseURL = getApiBaseUrl()
  return api.defaults.baseURL
}
