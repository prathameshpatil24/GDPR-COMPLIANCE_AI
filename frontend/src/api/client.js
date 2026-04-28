import axios from 'axios'

const api = axios.create({
  baseURL: '/',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300_000,
})

/**
 * Normalize FastAPI error detail (string or validation array).
 * @param {unknown} detail
 * @returns {string}
 */
function formatDetail(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((e) => (typeof e === 'object' && e?.msg ? e.msg : JSON.stringify(e)))
      .join('; ')
  }
  if (detail && typeof detail === 'object' && 'msg' in detail) return String(detail.msg)
  return 'Something went wrong'
}

/**
 * User-facing message from an axios/reject error.
 * @param {unknown} error
 * @returns {string}
 */
export function getErrorMessage(error) {
  if (axios.isAxiosError(error)) {
    if (error.code === 'ECONNABORTED') {
      return 'Analysis timed out. Try a shorter scenario or check if the backend is running.'
    }
    if (error.code === 'ERR_NETWORK' || !error.response) {
      return 'Cannot connect to the backend. Make sure `gdpr-check serve` is running on port 8000.'
    }
    const detail = error.response?.data?.detail
    const formatted = formatDetail(detail)
    if (formatted) return formatted
    return error.message || 'Analysis failed'
  }
  if (error instanceof Error) return error.message
  return 'Analysis failed'
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail
    const message = formatDetail(detail) || error.message || 'Something went wrong'
    console.error('API Error:', message)
    return Promise.reject(error)
  }
)

export default api

export const healthCheck = () => api.get('/health')

export const analyzeViolation = (scenario, projectId) =>
  api.post('/api/v1/analyze/violation', {
    scenario,
    ...(projectId ? { project_id: projectId } : {}),
  })

export const analyzeCompliance = (systemDescription, projectId) =>
  api.post('/api/v1/analyze/compliance', {
    system_description: systemDescription,
    ...(projectId ? { project_id: projectId } : {}),
  })

export const getHistory = (params = {}) => api.get('/api/v1/history', { params })

export const getAnalysisDetail = (id) => api.get(`/api/v1/history/${id}`)

export const getStats = () => api.get('/api/v1/stats')
