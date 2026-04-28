/* eslint-disable react-refresh/only-export-components -- Provider + hook */
import { createContext, useCallback, useContext, useEffect, useState } from 'react'

import { getStats } from '@/api/client'

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
      setTotalQueries(Number(res.data?.total_queries ?? 0))
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
