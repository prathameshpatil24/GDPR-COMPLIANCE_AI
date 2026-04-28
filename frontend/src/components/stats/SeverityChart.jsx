import { memo } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useChartColors } from '@/lib/chartTheme'

const ORDER = ['low', 'medium', 'high', 'critical', 'unknown']

const FILL = {
  low: '#34d399',
  medium: '#f59e0b',
  high: '#f97316',
  critical: '#f43f5e',
  unknown: '#64748b',
}

const LABELS = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
  unknown: 'Unknown',
}

/**
 * Donut of severity counts; optional click navigates to filtered history.
 * @param {{
 *   distribution: Record<string, number>,
 *   onSegmentClick?: (severityKey: string) => void,
 * }} props
 */
function SeverityChart({ distribution, onSegmentClick }) {
  const reduceMotion = useReducedMotion()
  const c = useChartColors()
  const dist = distribution && typeof distribution === 'object' ? distribution : {}

  const data = ORDER.filter((k) => (dist[k] ?? 0) > 0).map((key) => ({
    key,
    name: LABELS[key] ?? key,
    value: dist[key],
  }))

  const total = data.reduce((a, d) => a + d.value, 0)

  const tooltipStyle = {
    background: c.tooltipBg,
    border: `1px solid ${c.tooltipBorder}`,
    borderRadius: '0.5rem',
  }

  if (!data.length) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500">
        No severity data.
      </div>
    )
  }

  return (
    <div
      className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900"
      role="img"
      aria-label={`Severity distribution: ${total} queries`}
    >
      <h3 className="mb-4 text-lg font-medium text-slate-800 dark:text-slate-200">
        Severity distribution
      </h3>
      <div className="relative h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={2}
              isAnimationActive={!reduceMotion}
              animationDuration={800}
              cursor={onSegmentClick ? 'pointer' : 'default'}
              onClick={(_, index) => {
                const entry = data[index]
                if (entry && onSegmentClick) onSegmentClick(entry.key)
              }}
            >
              {data.map((entry) => (
                <Cell key={entry.key} fill={FILL[entry.key] ?? FILL.unknown} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: c.tooltipMuted, fontSize: 12 }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-center">
          <p className="font-mono text-2xl font-semibold text-slate-900 dark:text-slate-50">{total}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">queries</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap justify-center gap-x-4 gap-y-2">
        {data.map((d) => (
          <span
            key={d.key}
            className="inline-flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400"
          >
            <span className="h-2 w-2 rounded-full" style={{ background: FILL[d.key] }} aria-hidden />
            {d.name}: <span className="font-mono text-slate-800 dark:text-slate-200">{d.value}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

export default memo(SeverityChart)
