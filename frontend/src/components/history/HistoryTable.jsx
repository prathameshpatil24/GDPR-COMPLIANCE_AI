import { ChevronDown, ChevronUp } from 'lucide-react'
import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { Fragment, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import HistoryDetail from '@/components/history/HistoryDetail'
import SeverityBadge from '@/components/results/SeverityBadge'
import EmptyState from '@/components/shared/EmptyState'
import { cn } from '@/lib/utils'

/**
 * @param {string | null | undefined} s
 */
function parseTime(s) {
  if (!s) return 0
  const t = new Date(s).getTime()
  return Number.isNaN(t) ? 0 : t
}

/**
 * @param {number | null | undefined} ms
 */
function formatLatency(ms) {
  if (ms == null) return '—'
  const n = Number(ms)
  if (n >= 1000) return `${(n / 1000).toFixed(1)}s`
  return `${Math.round(n)}ms`
}

/**
 * @param {number | null | undefined} eur
 */
function formatCost(eur) {
  if (eur == null || Number.isNaN(Number(eur))) return '—'
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 4,
  }).format(Number(eur))
}

/**
 * @param {string} text
 * @param {number} max
 */
function truncate(text, max) {
  if (!text) return '—'
  if (text.length <= max) return text
  return `${text.slice(0, max)}…`
}

/**
 * @param {string} mode
 */
function modeLabel(mode) {
  if (mode === 'violation_analysis') return 'Violation'
  if (mode === 'compliance_assessment') return 'Compliance'
  return mode || '—'
}

/**
 * @param {{ active: boolean, ascending: boolean }} props
 */
function SortHeaderChevron({ active, ascending }) {
  if (!active) return null
  return ascending ? (
    <ChevronUp className="ml-1 inline h-3 w-3" aria-hidden />
  ) : (
    <ChevronDown className="ml-1 inline h-3 w-3" aria-hidden />
  )
}

/**
 * Sortable history table with expandable rows.
 * @param {{
 *   analyses: object[],
 *   expandedId: string | null,
 *   onToggleRow: (id: string) => void,
 *   detail: object | null,
 *   detailLoading: boolean,
 *   detailError: string | null,
 * }} props
 */
export default function HistoryTable({
  analyses,
  expandedId,
  onToggleRow,
  detail,
  detailLoading,
  detailError,
}) {
  const reduceMotion = useReducedMotion()
  const [sort, setSort] = useState({ key: 'created_at', dir: 'desc' })

  const sorted = useMemo(() => {
    const copy = [...analyses]
    copy.sort((a, b) => {
      const cmp = (() => {
        switch (sort.key) {
          case 'created_at':
            return parseTime(a.created_at) - parseTime(b.created_at)
          case 'mode':
            return (a.mode || '').localeCompare(b.mode || '')
          case 'scenario_system_description':
            return (a.scenario_system_description || '').localeCompare(
              b.scenario_system_description || ''
            )
          case 'severity':
            return (a.severity || '').localeCompare(b.severity || '')
          case 'cost_eur':
            return (Number(a.cost_eur) || 0) - (Number(b.cost_eur) || 0)
          case 'latency_ms':
            return (Number(a.latency_ms) || 0) - (Number(b.latency_ms) || 0)
          default:
            return 0
        }
      })()
      return sort.dir === 'asc' ? cmp : -cmp
    })
    return copy
  }, [analyses, sort])

  const toggleSort = (key) => {
    setSort((s) =>
      s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }
    )
  }

  if (!analyses.length) {
    return (
      <EmptyState
        title="No analyses found"
        description="Try adjusting your filters or run your first analysis."
        className="border-slate-200 dark:border-slate-800"
        action={
          <Link
            to="/"
            className="mt-4 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            Go to Analyze →
          </Link>
        }
      />
    )
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] table-fixed border-collapse text-left">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-100/80 dark:border-slate-800 dark:bg-slate-800/50">
              <th className="w-40 px-4 py-3">
                <button
                  type="button"
                  onClick={() => toggleSort('created_at')}
                  className="flex items-center text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500"
                >
                  Timestamp
                  <SortHeaderChevron
                    active={sort.key === 'created_at'}
                    ascending={sort.dir === 'asc'}
                  />
                </button>
              </th>
              <th className="w-28 px-4 py-3">
                <button
                  type="button"
                  onClick={() => toggleSort('mode')}
                  className="flex items-center text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500"
                >
                  Mode
                  <SortHeaderChevron active={sort.key === 'mode'} ascending={sort.dir === 'asc'} />
                </button>
              </th>
              <th className="px-4 py-3">
                <button
                  type="button"
                  onClick={() => toggleSort('scenario_system_description')}
                  className="flex items-center text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500"
                >
                  Scenario
                  <SortHeaderChevron
                    active={sort.key === 'scenario_system_description'}
                    ascending={sort.dir === 'asc'}
                  />
                </button>
              </th>
              <th className="w-28 px-4 py-3">
                <button
                  type="button"
                  onClick={() => toggleSort('severity')}
                  className="flex items-center text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500"
                >
                  Severity
                  <SortHeaderChevron
                    active={sort.key === 'severity'}
                    ascending={sort.dir === 'asc'}
                  />
                </button>
              </th>
              <th className="hidden w-24 px-4 py-3 lg:table-cell">
                <button
                  type="button"
                  onClick={() => toggleSort('cost_eur')}
                  className="flex items-center text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500"
                >
                  Cost
                  <SortHeaderChevron
                    active={sort.key === 'cost_eur'}
                    ascending={sort.dir === 'asc'}
                  />
                </button>
              </th>
              <th className="hidden w-24 px-4 py-3 lg:table-cell">
                <button
                  type="button"
                  onClick={() => toggleSort('latency_ms')}
                  className="flex items-center text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500"
                >
                  Latency
                  <SortHeaderChevron
                    active={sort.key === 'latency_ms'}
                    ascending={sort.dir === 'asc'}
                  />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, index) => {
              const isOpen = expandedId === row.id
              return (
                <Fragment key={row.id}>
                  <motion.tr
                    tabIndex={0}
                    initial={reduceMotion ? false : { opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: reduceMotion ? 0 : index * 0.03, duration: 0.2 }}
                    onClick={() => onToggleRow(row.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onToggleRow(row.id)
                      }
                    }}
                    className={cn(
                      'cursor-pointer border-b border-slate-200 transition-colors hover:bg-slate-100/80 dark:border-slate-800/50 dark:hover:bg-slate-800/30',
                      isOpen && 'bg-slate-50 dark:bg-slate-800/20'
                    )}
                  >
                    <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                      {row.created_at
                        ? new Date(row.created_at).toLocaleString()
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                          row.mode === 'violation_analysis'
                            ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'
                            : 'bg-slate-500/10 text-slate-600 dark:text-slate-400'
                        )}
                      >
                        {modeLabel(row.mode)}
                      </span>
                    </td>
                    <td className="max-w-[10rem] truncate px-4 py-3 text-sm text-slate-800 dark:text-slate-200 sm:max-w-[14rem] lg:max-w-none lg:whitespace-normal">
                      {truncate(row.scenario_system_description || '', 100)}
                    </td>
                    <td className="px-4 py-3">
                      <SeverityBadge level={row.severity || 'unknown'} />
                    </td>
                    <td className="hidden px-4 py-3 font-mono text-xs text-slate-500 lg:table-cell dark:text-slate-400">
                      {formatCost(row.cost_eur)}
                    </td>
                    <td className="hidden px-4 py-3 font-mono text-xs text-slate-500 lg:table-cell dark:text-slate-400">
                      {formatLatency(row.latency_ms)}
                    </td>
                  </motion.tr>
                  {isOpen ? (
                    <tr className="border-b border-slate-200 dark:border-slate-800/50">
                      <td colSpan={6} className="p-0">
                        <HistoryDetail
                          detail={detail}
                          loading={detailLoading}
                          error={detailError}
                          onCollapse={() => onToggleRow(row.id)}
                        />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
