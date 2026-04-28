import { useReducedMotion } from 'framer-motion'
import {
  Bar,
  BarChart,
  CartesianGrid,
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
 * Queries per day bar chart.
 * @param {{ data: Array<{ date?: string, count?: number }> }} props
 */
export default function QueryChart({ data }) {
  const reduceMotion = useReducedMotion()
  const rows = Array.isArray(data) ? data : []

  if (!rows.length) {
    return (
      <div className="flex h-[250px] items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500">
        No query volume data.
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="mb-4 text-lg font-medium text-slate-800 dark:text-slate-200">Queries per day</h3>
      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgb(51 65 85)"
              strokeOpacity={0.35}
              horizontal={false}
            />
            <XAxis dataKey="date" tick={{ fill: 'rgb(148 163 184)', fontSize: 12 }} />
            <YAxis tick={{ fill: 'rgb(148 163 184)', fontSize: 12 }} allowDecimals={false} />
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: 'rgb(148 163 184)', fontSize: 12 }}
              formatter={(v) => [`${v} queries`, 'Count']}
            />
            <Bar
              dataKey="count"
              fill="rgb(99 102 241)"
              radius={[4, 4, 0, 0]}
              activeBar={{ fill: 'rgb(129 140 248)' }}
              isAnimationActive={!reduceMotion}
              animationDuration={600}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
