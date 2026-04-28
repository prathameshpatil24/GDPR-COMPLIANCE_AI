import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import HistoryFilters from '@/components/history/HistoryFilters'
import HistoryTable from '@/components/history/HistoryTable'
import { Button } from '@/components/ui/button'
import Skeleton from '@/components/shared/Skeleton'
import { useAnalysisDetail, useHistory } from '@/hooks/useHistory'

/**
 * Past analyses with filters, sorting, and inline report expansion.
 */
export default function HistoryPage() {
  const [searchParams] = useSearchParams()
  const severityParam = searchParams.get('severity')
  const { analyses, allAnalyses, loading, error, filters, setFilters, refetch } = useHistory({
    initialSeverity: severityParam,
    limit: 500,
  })
  const [expandedId, setExpandedId] = useState(null)
  const { detail, loading: detailLoading, error: detailError } = useAnalysisDetail(expandedId)

  const toggleRow = useCallback((id) => {
    setExpandedId((cur) => (cur === id ? null : id))
  }, [])

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape' && expandedId) {
        setExpandedId(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [expandedId])

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Analysis history</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Browse past runs from the app database. Expand a row for the full report.
        </p>
      </div>

      <HistoryFilters
        filters={filters}
        setFilters={setFilters}
        filteredCount={analyses.length}
        totalCount={allAnalyses.length}
      />

      {error ? (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-700 dark:text-rose-400"
        >
          <span>{error}</span>
          <Button type="button" size="sm" variant="secondary" onClick={() => void refetch()}>
            Retry
          </Button>
        </div>
      ) : null}

      {loading ? (
        <div className="space-y-2 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : (
        <HistoryTable
          analyses={analyses}
          expandedId={expandedId}
          onToggleRow={toggleRow}
          detail={detail}
          detailLoading={detailLoading}
          detailError={detailError}
        />
      )}
    </div>
  )
}
