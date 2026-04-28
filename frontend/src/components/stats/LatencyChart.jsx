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
 * Daily average latency (ms → seconds on axis).
 * @param {{ data: Array<{ date?: string, avg_latency_ms?: number }> }} props
 */
export default function LatencyChart({ data }) {
  const reduceMotion = useReducedMotion()
  const rows = (Array.isArray(data) ? data : []).map((d) => ({
    ...d,
    latency_s: (Number(d.avg_latency_ms) || 0) / 1000,
  }))

  if (!rows.length) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500">
        No latency data for the selected period.
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="mb-4 text-lg font-medium text-slate-800 dark:text-slate-200">
        Avg latency over time
      </h3>
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
              dataKey="latency_s"
              tick={{ fill: 'rgb(148 163 184)', fontSize: 12 }}
              tickFormatter={(v) => `${Number(v).toFixed(1)}s`}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const ms = payload[0]?.payload?.avg_latency_ms
                const s = (Number(ms) || 0) / 1000
                return (
                  <div
                    className="rounded-lg border border-slate-700 bg-slate-800 p-3 shadow-lg"
                    style={tooltipStyle}
                  >
                    <p className="text-xs text-slate-400">{label}</p>
                    <p className="text-sm text-slate-100">{s.toFixed(1)}s avg</p>
                  </div>
                )
              }}
            />
            <Area
              type="monotone"
              dataKey="latency_s"
              fill="rgb(245 158 11)"
              fillOpacity={0.1}
              stroke="none"
            />
            <Line
              type="monotone"
              dataKey="latency_s"
              stroke="rgb(245 158 11)"
              strokeWidth={2}
              dot={{ fill: 'rgb(245 158 11)', r: 3 }}
              isAnimationActive={!reduceMotion}
              animationDuration={1000}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
