import { memo } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useChartColors } from '@/lib/chartTheme'

/**
 * Queries per day bar chart.
 * @param {{ data: Array<{ date?: string, count?: number }> }} props
 */
function QueryChart({ data }) {
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
        className="flex h-[250px] items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500"
        role="img"
        aria-label="Queries per day: no data"
      >
        No query volume data.
      </div>
    )
  }

  return (
    <div
      className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900"
      role="img"
      aria-label="Number of analyses per day"
    >
      <h3 className="mb-4 text-lg font-medium text-slate-800 dark:text-slate-200">Queries per day</h3>
      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={c.grid}
              strokeOpacity={0.45}
              horizontal={false}
            />
            <XAxis dataKey="date" tick={{ fill: c.axis, fontSize: 12 }} />
            <YAxis tick={{ fill: c.axis, fontSize: 12 }} allowDecimals={false} />
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: c.tooltipMuted, fontSize: 12 }}
              formatter={(v) => [`${v} queries`, 'Count']}
            />
            <Bar
              dataKey="count"
              fill={c.primary}
              radius={[4, 4, 0, 0]}
              activeBar={{ fill: '#818cf8' }}
              isAnimationActive={!reduceMotion}
              animationDuration={600}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default memo(QueryChart)
