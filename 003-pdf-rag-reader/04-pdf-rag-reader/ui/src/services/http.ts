import axios from 'axios'

export class ApiError extends Error {
  readonly status?: number
  readonly code: string
  readonly ambiguous: boolean

  constructor(message: string, code: string, status?: number, ambiguous = false) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.ambiguous = ambiguous
  }
}

// Chat and deletion may wait for local model work; callers can override timeout.
// No automatic retries: a lost response may follow a successful mutation.
export function createHttpClient(baseURL = '/api') {
  const client = axios.create({ baseURL, timeout: 300_000 })
  client.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
      if (!axios.isAxiosError(error)) return Promise.reject(error)
      const status = error.response?.status
      const envelope = error.response?.data?.error
      const method = error.config?.method?.toUpperCase()
      const ambiguous = !status && method !== undefined && !['GET', 'HEAD', 'OPTIONS'].includes(method)
      const timedOut = error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT'
      const message = typeof envelope?.message === 'string' ? envelope.message
        : timedOut ? 'The API request timed out. Refresh before retrying to check whether it completed.'
        : status ? `Request failed (${status}). Please try again.`
        : 'Could not reach the API. Check the backend connection and try again.'
      const code = typeof envelope?.code === 'string' ? envelope.code
        : timedOut ? 'request_timeout' : status ? 'http_error' : 'network_error'
      return Promise.reject(new ApiError(message, code, status, ambiguous))
    },
  )
  return client
}

export const http = createHttpClient(import.meta.env?.VITE_API_BASE_URL || '/api')
