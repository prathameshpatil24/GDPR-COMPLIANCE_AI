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
 * Daily average latency (ms → seconds on axis).
 * @param {{ data: Array<{ date?: string, avg_latency_ms?: number }> }} props
 */
function LatencyChart({ data }) {
  const reduceMotion = useReducedMotion()
  const c = useChartColors()
  const rows = (Array.isArray(data) ? data : []).map((d) => ({
    ...d,
    latency_s: (Number(d.avg_latency_ms) || 0) / 1000,
  }))

  if (!rows.length) {
    return (
      <div
        className="flex h-[300px] items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-500"
        role="img"
        aria-label="Latency chart: no data"
      >
        No latency data for the selected period.
      </div>
    )
  }

  return (
    <div
      className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900"
      role="img"
      aria-label="Average latency over time in seconds"
    >
      <h3 className="mb-4 text-lg font-medium text-slate-800 dark:text-slate-200">
        Avg latency over time
      </h3>
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={c.grid} strokeOpacity={0.45} />
            <XAxis dataKey="date" tick={{ fill: c.axis, fontSize: 12 }} />
            <YAxis
              dataKey="latency_s"
              tick={{ fill: c.axis, fontSize: 12 }}
              tickFormatter={(v) => `${Number(v).toFixed(1)}s`}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const ms = payload[0]?.payload?.avg_latency_ms
                const s = (Number(ms) || 0) / 1000
                return (
                  <div
                    className="rounded-lg border p-3 shadow-lg"
                    style={{
                      background: c.tooltipBg,
                      borderColor: c.tooltipBorder,
                      color: c.tooltipText,
                    }}
                  >
                    <p className="text-xs" style={{ color: c.tooltipMuted }}>
                      {label}
                    </p>
                    <p className="text-sm">{s.toFixed(1)}s avg</p>
                  </div>
                )
              }}
            />
            <Area
              type="monotone"
              dataKey="latency_s"
              fill={c.amber}
              fillOpacity={0.12}
              stroke="none"
            />
            <Line
              type="monotone"
              dataKey="latency_s"
              stroke={c.amber}
              strokeWidth={2}
              dot={{ fill: c.amber, r: 3 }}
              isAnimationActive={!reduceMotion}
              animationDuration={1000}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default memo(LatencyChart)
