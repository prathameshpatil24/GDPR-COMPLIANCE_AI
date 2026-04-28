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

/** @returns {Promise<import('axios').AxiosResponse<{ status: string; version: string }>>} */
export const healthCheck = () => api.get('/health')

/**
 * @param {string} scenario
 * @param {string} [projectId]
 */
export const analyzeViolation = (scenario, projectId) =>
  api.post('/api/v1/analyze/violation', {
    scenario,
    ...(projectId ? { project_id: projectId } : {}),
  })

/**
 * @param {string} systemDescription
 * @param {string} [projectId]
 */
export const analyzeCompliance = (systemDescription, projectId) =>
  api.post('/api/v1/analyze/compliance', {
    system_description: systemDescription,
    ...(projectId ? { project_id: projectId } : {}),
  })
