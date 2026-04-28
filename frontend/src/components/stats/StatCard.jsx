import Card from '@/components/shared/Card'
import { cn } from '@/lib/utils'

/**
 * KPI tile for dashboard.
 * @param {{ label: string, value: string | number, hint?: string, className?: string }} props
 */
export default function StatCard({ label, value, hint, className }) {
  return (
    <Card className={cn(className)}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-2 font-mono text-2xl font-semibold text-slate-900 dark:text-slate-50">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">{hint}</p> : null}
    </Card>
  )
}
