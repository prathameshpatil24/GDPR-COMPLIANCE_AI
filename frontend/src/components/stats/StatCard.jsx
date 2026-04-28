import { animate } from 'framer-motion'
import { useEffect, useState } from 'react'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { cn } from '@/lib/utils'

/**
 * KPI card with optional count-up animation.
 * @param {{
 *   label: string,
 *   subtitle?: string,
 *   icon?: import('react').ComponentType<{ className?: string; 'aria-hidden'?: boolean }>,
 *   value: number,
 *   format: (n: number) => string,
 *   className?: string,
 * }} props
 */
export default function StatCard({ label, subtitle, icon: Icon, value, format, className }) {
  const reduceMotion = useReducedMotion()
  const [display, setDisplay] = useState(0)
  const target = Number(value) || 0

  useEffect(() => {
    const controls = animate(0, target, {
      duration: reduceMotion ? 0 : 0.8,
      ease: [0, 0, 0.2, 1],
      onUpdate: (latest) => setDisplay(latest),
    })
    return () => controls.stop()
  }, [target, reduceMotion])

  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900',
        className
      )}
    >
      <div className="flex items-center gap-2">
        {Icon ? <Icon className="h-5 w-5 shrink-0 text-slate-500 dark:text-slate-500" aria-hidden /> : null}
        <p className="text-sm text-slate-600 dark:text-slate-400">{label}</p>
      </div>
      <p className="mt-2 font-mono text-3xl font-semibold text-slate-900 dark:text-slate-50">
        {format(display)}
      </p>
      {subtitle ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">{subtitle}</p> : null}
    </div>
  )
}
