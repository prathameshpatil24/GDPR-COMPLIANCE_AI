import { memo } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import Card from '@/components/shared/Card'
import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useChartColors } from '@/lib/chartTheme'

const FILL = {
  compliant: '#10b981',
  at_risk: '#f59e0b',
  non_compliant: '#f43f5e',
  insufficient_info: '#64748b',
}

const LABELS = {
  compliant: 'Compliant',
  at_risk: 'At risk',
  non_compliant: 'Non-compliant',
  insufficient_info: 'Insufficient info',
}

/**
 * Donut of finding status counts.
 * @param {{ findings: Array<{ status?: string }> }} props
 */
function RiskOverviewChart({ findings }) {
  const reduceMotion = useReducedMotion()
  const c = useChartColors()
  const counts = {}
  for (const f of findings || []) {
    const s = String(f.status || '').toLowerCase().replace(/-/g, '_')
    const key = s === 'noncompliant' ? 'non_compliant' : s
    if (!FILL[key]) continue
    counts[key] = (counts[key] || 0) + 1
  }
  const data = Object.entries(counts).map(([key, value]) => ({
    key,
    name: LABELS[key] ?? key,
    value,
  }))
  const total = data.reduce((a, d) => a + d.value, 0)

  if (!data.length) return null

  const tooltipStyle = {
    background: c.tooltipBg,
    border: `1px solid ${c.tooltipBorder}`,
    borderRadius: '0.5rem',
  }

  return (
    <Card>
      <h3 className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-50">Risk overview</h3>
      <div
        className="relative h-64 w-full"
        role="img"
        aria-label={`Risk overview donut: ${total} findings`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={58}
              outerRadius={82}
              paddingAngle={2}
              isAnimationActive={!reduceMotion}
              animationDuration={800}
            >
              {data.map((entry) => (
                <Cell key={entry.key} fill={FILL[entry.key]} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: c.tooltipMuted, fontSize: 12 }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: c.axis }} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-center">
          <p className="font-mono text-2xl font-semibold text-slate-900 dark:text-slate-50">{total}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">findings</p>
        </div>
      </div>
    </Card>
  )
}

export default memo(RiskOverviewChart)
