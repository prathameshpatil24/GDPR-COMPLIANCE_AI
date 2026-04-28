/* eslint-disable react-refresh/only-export-components -- Provider + hook */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { getHistory } from '@/api/client'

const AnalysisCountContext = createContext({
  /** @type {number | null} */
  count: null,
  refresh: async () => {},
  /** Optimistic +1 after a successful analysis (server refresh still runs). */
  increment: () => {},
})

/**
 * Count of stored analyses (same source as History), not query-log totals from /stats.
 * @param {{ children: import('react').ReactNode }} props
 */
export function AnalysisCountProvider({ children }) {
  const [count, setCount] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const res = await getHistory({ limit: 500 })
      const list = res.data?.analyses
      setCount(Array.isArray(list) ? list.length : 0)
    } catch {
      setCount(null)
    }
  }, [])

  const increment = useCallback(() => {
    setCount((c) => (c == null ? null : c + 1))
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => {
      void refresh()
    }, 0)
    return () => window.clearTimeout(id)
  }, [refresh])

  const value = useMemo(
    () => ({
      count,
      refresh,
      increment,
    }),
    [count, refresh, increment]
  )

  return (
    <AnalysisCountContext.Provider value={value}>{children}</AnalysisCountContext.Provider>
  )
}

export function useAnalysisCount() {
  return useContext(AnalysisCountContext)
}
