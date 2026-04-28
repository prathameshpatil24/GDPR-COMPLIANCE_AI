import { memo } from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useChartColors } from '@/lib/chartTheme'

/**
 * Daily cost line + area chart.
 * @param {{ data: Array<{ date?: string, cost_eur?: number }> }} props
 */
function CostChart({ data }) {
  const reduceMotion = useReducedMotion()
  const c = useChartColors()
  const rows = Array.isArray(data) ? data : []

  const tooltipStyle = {
    background: c.tooltipBg,
    border: `1px solid ${c.tooltipBorder}`,
    borderRadius: '0.5rem',
  }

  if (!rows.length) {
    return (
      <div
        className="flex h-[300px] items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500"
        role="img"
        aria-label="Cost over time chart: no data"
      >
        No cost data for the selected period.
      </div>
    )
  }

  return (
    <div
      className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900"
      role="img"
      aria-label="Cost in EUR over time"
    >
      <h3 className="mb-4 text-lg font-medium text-slate-800 dark:text-slate-200">Cost over time</h3>
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={c.grid} strokeOpacity={0.45} />
            <XAxis dataKey="date" tick={{ fill: c.axis, fontSize: 12 }} />
            <YAxis
              tick={{ fill: c.axis, fontSize: 12 }}
              tickFormatter={(v) => `€${Number(v).toFixed(2)}`}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: c.tooltipMuted, fontSize: 12 }}
              formatter={(val) => [`€${Number(val).toFixed(4)}`, 'Cost']}
            />
            <Area
              type="monotone"
              dataKey="cost_eur"
              fill={c.primary}
              fillOpacity={0.12}
              stroke="none"
            />
            <Line
              type="monotone"
              dataKey="cost_eur"
              stroke={c.primary}
              strokeWidth={2}
              dot={{ fill: c.primary, r: 3 }}
              isAnimationActive={!reduceMotion}
              animationDuration={1000}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default memo(CostChart)
