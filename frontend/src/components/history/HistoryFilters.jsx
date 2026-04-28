import { Search } from 'lucide-react'

import { cn } from '@/lib/utils'

const MODE_OPTIONS = [
  { id: 'all', label: 'All' },
  { id: 'violation', label: 'Violation' },
  { id: 'compliance', label: 'Compliance' },
]

const SEVERITY_OPTIONS = [
  { id: null, label: 'All', dot: 'bg-slate-500' },
  { id: 'low', label: 'Low', dot: 'bg-emerald-400' },
  { id: 'medium', label: 'Medium', dot: 'bg-amber-500' },
  { id: 'high', label: 'High', dot: 'bg-orange-500' },
  { id: 'critical', label: 'Critical', dot: 'bg-rose-500' },
]

/**
 * Filter bar for history list.
 * @param {{
 *   filters: object,
 *   setFilters: (fn: (p: object) => object) => void,
 *   filteredCount: number,
 *   totalCount: number,
 * }} props
 */
export default function HistoryFilters({ filters, setFilters, filteredCount, totalCount }) {
  return (
    <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-center lg:gap-3">
      <div className="inline-flex rounded-lg bg-slate-200/80 p-1 dark:bg-slate-800/50">
        {MODE_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            type="button"
            onClick={() => setFilters((f) => ({ ...f, mode: opt.id }))}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm transition-colors',
              filters.mode === opt.id
                ? 'bg-white font-medium text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-100'
                : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="inline-flex flex-wrap items-center gap-1 rounded-lg bg-slate-200/80 p-1 dark:bg-slate-800/50">
        {SEVERITY_OPTIONS.map((opt) => (
          <button
            key={opt.id ?? 'all-sev'}
            type="button"
            onClick={() => setFilters((f) => ({ ...f, severity: opt.id }))}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm transition-colors',
              filters.severity === opt.id
                ? 'bg-white font-medium text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-100'
                : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
            )}
          >
            <span className={cn('h-2 w-2 shrink-0 rounded-full', opt.dot)} aria-hidden />
            {opt.label}
          </button>
        ))}
      </div>

      <div className="relative min-w-[200px] flex-1 lg:max-w-md">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
          aria-hidden
        />
        <input
          type="search"
          value={filters.search}
          onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          placeholder="Search scenarios…"
          className="w-full rounded-lg border border-slate-300 bg-white py-1.5 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-100 dark:placeholder:text-slate-500"
        />
      </div>

      <p className="ml-auto text-sm text-slate-500 dark:text-slate-500">
        Showing {filteredCount} of {totalCount} analyses
      </p>
    </div>
  )
}
