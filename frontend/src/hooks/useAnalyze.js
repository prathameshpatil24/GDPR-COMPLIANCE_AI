import { useAnalyzeContext } from '@/context/AnalyzeContext'

export { useAnalyzeContext }

/**
 * Run violation or compliance analysis with loading / elapsed / error state (session-persisted).
 */
export function useAnalyze() {
  return useAnalyzeContext()
}
