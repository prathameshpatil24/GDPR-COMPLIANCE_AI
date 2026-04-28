import { useMemo } from 'react'
import { useReducedMotion } from '@/hooks/useReducedMotion'
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

/**
 * Horizontal bars for violation confidences by article.
 * @param {{ violations: Array<{ article_reference?: string, confidence?: number }> }} props
 */
export default function ViolationArticleChart({ violations }) {
  const reduceMotion = useReducedMotion()
  const data = useMemo(() => {
    return (violations || [])
      .map((v) => ({
        article: v.article_reference || '—',
        confidence: Number(v.confidence) || 0,
      }))
      .sort((a, b) => b.confidence - a.confidence)
  }, [violations])

  if (!data.length) return null

  return (
    <Card>
      <h3 className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-50">
        Article confidence
      </h3>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ left: 8, right: 16, top: 8, bottom: 8 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgb(51 65 85)"
              strokeOpacity={0.35}
              horizontal={false}
            />
            <XAxis
              type="number"
              domain={[0, 1]}
              tick={{ fill: 'rgb(148 163 184)', fontSize: 11 }}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
            />
            <YAxis
              type="category"
              dataKey="article"
              width={140}
              tick={{ fill: 'rgb(148 163 184)', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
            />
            <Tooltip
              contentStyle={{
                background: 'rgb(30 41 59)',
                border: '1px solid rgb(51 65 85)',
                borderRadius: '0.5rem',
              }}
            />
            <Bar
              dataKey="confidence"
              fill="rgb(99 102 241)"
              radius={[0, 4, 4, 0]}
              isAnimationActive={!reduceMotion}
              animationDuration={600}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}
