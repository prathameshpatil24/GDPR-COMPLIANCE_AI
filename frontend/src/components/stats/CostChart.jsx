import { useReducedMotion } from 'framer-motion'
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

const tooltipStyle = {
  background: 'rgb(30 41 59)',
  border: '1px solid rgb(51 65 85)',
  borderRadius: '0.5rem',
}

/**
 * Daily cost line + area chart.
 * @param {{ data: Array<{ date?: string, cost_eur?: number }> }} props
 */
export default function CostChart({ data }) {
  const reduceMotion = useReducedMotion()
  const rows = Array.isArray(data) ? data : []

  if (!rows.length) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500">
        No cost data for the selected period.
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="mb-4 text-lg font-medium text-slate-800 dark:text-slate-200">Cost over time</h3>
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgb(51 65 85)"
              strokeOpacity={0.35}
            />
            <XAxis dataKey="date" tick={{ fill: 'rgb(148 163 184)', fontSize: 12 }} />
            <YAxis
              tick={{ fill: 'rgb(148 163 184)', fontSize: 12 }}
              tickFormatter={(v) => `€${Number(v).toFixed(2)}`}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: 'rgb(148 163 184)', fontSize: 12 }}
              formatter={(val) => [`€${Number(val).toFixed(4)}`, 'Cost']}
            />
            <Area
              type="monotone"
              dataKey="cost_eur"
              fill="rgb(99 102 241)"
              fillOpacity={0.1}
              stroke="none"
            />
            <Line
              type="monotone"
              dataKey="cost_eur"
              stroke="rgb(99 102 241)"
              strokeWidth={2}
              dot={{ fill: 'rgb(99 102 241)', r: 3 }}
              isAnimationActive={!reduceMotion}
              animationDuration={1000}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
