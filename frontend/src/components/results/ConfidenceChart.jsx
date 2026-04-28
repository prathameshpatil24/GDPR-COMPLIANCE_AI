import { memo, useMemo } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import Card from '@/components/shared/Card'
import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useChartColors } from '@/lib/chartTheme'
import { shortArticleAxisLabel } from '@/lib/articleAxisLabel'

/**
 * Horizontal bar chart of relative article emphasis (mention count / max).
 * @param {{ findings: Array<{ relevant_articles?: string[] }> }} props
 */
function ConfidenceChart({ findings }) {
  const reduceMotion = useReducedMotion()
  const c = useChartColors()
  const data = useMemo(() => {
    const counts = {}
    for (const f of findings || []) {
      for (const a of f.relevant_articles || []) {
        counts[a] = (counts[a] || 0) + 1
      }
    }
    const max = Math.max(...Object.values(counts), 1)
    return Object.entries(counts)
      .map(([articleFull, n]) => ({
        articleFull,
        articleShort: shortArticleAxisLabel(articleFull),
        weight: n / max,
      }))
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 16)
  }, [findings])

  if (!data.length) return null

  const chartHeight = Math.max(250, data.length * 40)

  return (
    <Card>
      <h3 className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-50">
        Article emphasis (relative)
      </h3>
      <div
        className="w-full"
        style={{ height: chartHeight }}
        role="img"
        aria-label="Relative article emphasis bar chart"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ left: 88, right: 20, top: 12, bottom: 12 }}
            barCategoryGap="12%"
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={c.grid}
              strokeOpacity={0.45}
              horizontal={false}
            />
            <XAxis
              type="number"
              domain={[0, 1]}
              tick={{ fill: c.axis, fontSize: 11 }}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
            />
            <YAxis
              type="category"
              dataKey="articleShort"
              width={84}
              tick={{ fill: c.axis, fontSize: 11 }}
              interval={0}
            />
            <Tooltip
              cursor={{ fill: c.primaryArea }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const row = payload[0]?.payload
                if (!row) return null
                const pct = Math.round((row.weight ?? 0) * 100)
                return (
                  <div
                    className="rounded-lg border p-3 shadow-lg"
                    style={{
                      background: c.tooltipBg,
                      borderColor: c.tooltipBorder,
                    }}
                  >
                    <p className="text-sm font-medium" style={{ color: c.tooltipText }}>
                      {row.articleFull}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: c.tooltipMuted }}>
                      {pct}% relative emphasis
                    </p>
                  </div>
                )
              }}
            />
            <Bar
              dataKey="weight"
              fill={c.primary}
              radius={[0, 4, 4, 0]}
              barSize={16}
              isAnimationActive={!reduceMotion}
              animationDuration={600}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

export default memo(ConfidenceChart)
