import { memo } from 'react'

/**
 * Violation vs compliance split from mode_distribution.
 * @param {{ distribution: Record<string, number> }} props
 */
function ModeChart({ distribution }) {
  const dist = distribution && typeof distribution === 'object' ? distribution : {}
  const v = dist.violation_analysis ?? 0
  const c = dist.compliance_assessment ?? 0
  const total = v + c

  if (!total) {
    return (
      <div className="flex min-h-[120px] items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500">
        No mode data.
      </div>
    )
  }

  const pv = Math.round((v / total) * 100)
  const pc = 100 - pv

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="mb-4 text-lg font-medium text-slate-800 dark:text-slate-200">Analysis modes</h3>
      <div className="flex h-3 overflow-hidden rounded-full">
        <div
          className="bg-indigo-500 transition-all"
          style={{ width: `${pv}%` }}
          title={`Violation ${v}`}
        />
        <div
          className="bg-slate-500 transition-all"
          style={{ width: `${pc}%` }}
          title={`Compliance ${c}`}
        />
      </div>
      <div className="mt-3 space-y-1 text-sm">
        <p className="flex justify-between text-slate-600 dark:text-slate-400">
          <span className="inline-flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-indigo-500" aria-hidden />
            Violation
          </span>
          <span className="font-mono text-slate-800 dark:text-slate-200">
            {v} ({pv}%)
          </span>
        </p>
        <p className="flex justify-between text-slate-600 dark:text-slate-400">
          <span className="inline-flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-slate-500" aria-hidden />
            Compliance
          </span>
          <span className="font-mono text-slate-800 dark:text-slate-200">
            {c} ({pc}%)
          </span>
        </p>
      </div>
    </div>
  )
}

export default memo(ModeChart)
