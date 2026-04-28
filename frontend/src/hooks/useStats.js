import { useCallback, useEffect, useState } from 'react'

import { getStats, getErrorMessage } from '@/api/client'

/** Fetch dashboard stats from `/api/v1/stats`. */
export function useStats() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getStats()
      setStats(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
      setStats(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => {
      void load()
    }, 0)
    return () => window.clearTimeout(id)
  }, [load])

  return { stats, loading, error, refetch: load }
}
