/* eslint-disable react-refresh/only-export-components -- Provider + hook */
import { createContext, useCallback, useContext, useEffect, useState } from 'react'

import { getHistory, getStats } from '@/api/client'

const NavMetricsContext = createContext({
  /** @type {number | null} */
  totalQueries: null,
  refresh: async () => {},
})

/**
 * @param {{ children: import('react').ReactNode }} props
 */
export function NavMetricsProvider({ children }) {
  const [totalQueries, setTotalQueries] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const res = await getStats()
      const raw = res.data?.total_queries
      const n = typeof raw === 'number' ? raw : Number.parseInt(String(raw), 10)
      if (Number.isFinite(n) && n >= 0) {
        setTotalQueries(Math.floor(n))
        return
      }
    } catch {
      /* try history fallback */
    }
    try {
      const res = await getHistory({ limit: 500 })
      const list = res.data?.analyses
      setTotalQueries(Array.isArray(list) ? list.length : 0)
    } catch {
      setTotalQueries(null)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => {
      void refresh()
    }, 0)
    return () => window.clearTimeout(id)
  }, [refresh])

  return (
    <NavMetricsContext.Provider value={{ totalQueries, refresh }}>{children}</NavMetricsContext.Provider>
  )
}

export function useNavMetrics() {
  return useContext(NavMetricsContext)
}
