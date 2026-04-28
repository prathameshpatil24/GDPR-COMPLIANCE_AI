import { useCallback, useEffect, useMemo, useState } from 'react'

import { getAnalysisDetail, getHistory, getErrorMessage } from '@/api/client'

/**
 * @typedef {'all' | 'violation' | 'compliance'} HistoryModeFilter
 */

/**
 * Fetch history with server mode filter and client severity/search filters.
 * @param {{ initialSeverity?: string | null, limit?: number }} [options]
 */
export function useHistory(options = {}) {
  const { initialSeverity = null, limit = 500 } = options
  const [rawAnalyses, setRawAnalyses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState(() => ({
    mode: /** @type {HistoryModeFilter} */ ('all'),
    severity: /** @type {string | null} */ (initialSeverity ?? null),
    search: '',
  }))

  useEffect(() => {
    const t = window.setTimeout(() => {
      setFilters((f) => ({ ...f, severity: initialSeverity ?? null }))
    }, 0)
    return () => window.clearTimeout(t)
  }, [initialSeverity])

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { limit }
      if (filters.mode === 'violation') params.mode = 'violation_analysis'
      else if (filters.mode === 'compliance') params.mode = 'compliance_assessment'
      const response = await getHistory(params)
      const list = response.data?.analyses ?? []
      setRawAnalyses(Array.isArray(list) ? list : [])
    } catch (err) {
      setError(getErrorMessage(err))
      setRawAnalyses([])
    } finally {
      setLoading(false)
    }
  }, [filters.mode, limit])

  useEffect(() => {
    const id = window.setTimeout(() => {
      void fetchHistory()
    }, 0)
    return () => window.clearTimeout(id)
  }, [fetchHistory])

  const filtered = useMemo(() => {
    return rawAnalyses.filter((a) => {
      if (filters.severity) {
        const sev = (a.severity || '').toLowerCase().trim()
        const want = filters.severity.toLowerCase().trim()
        if (sev !== want) return false
      }
      if (filters.search.trim()) {
        const q = filters.search.toLowerCase().trim()
        const text = (a.scenario_system_description || '').toLowerCase()
        if (!text.includes(q)) return false
      }
      return true
    })
  }, [rawAnalyses, filters.severity, filters.search])

  return {
    analyses: filtered,
    allAnalyses: rawAnalyses,
    loading,
    error,
    filters,
    setFilters,
    refetch: fetchHistory,
  }
}

/**
 * Load one analysis by id for expanded history row.
 * @param {string | null} id
 */
export function useAnalysisDetail(id) {
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!id) {
      const t = window.setTimeout(() => {
        setDetail(null)
        setError(null)
        setLoading(false)
      }, 0)
      return () => window.clearTimeout(t)
    }
    let cancelled = false
    const runId = window.setTimeout(() => {
      if (cancelled) return
      setLoading(true)
      setError(null)
      setDetail(null)
      getAnalysisDetail(id)
        .then((res) => {
          if (!cancelled) setDetail(res.data)
        })
        .catch((err) => {
          if (!cancelled) setError(getErrorMessage(err))
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, 0)
    return () => {
      cancelled = true
      window.clearTimeout(runId)
    }
  }, [id])

  return { detail, loading, error }
}
