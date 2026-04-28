import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'

import { formatConfidence } from '@/lib/formatters'

/**
 * Horizontal 0–1 confidence bar with animated fill.
 * @param {{ value: number, className?: string }} props
 */
export default function ConfidenceBar({ value, className }) {
  const reduceMotion = useReducedMotion()
  const pct = Math.max(0, Math.min(100, (Number(value) || 0) * 100))

  return (
    <div className={`flex items-center gap-3 ${className ?? ''}`}>
      <div className="h-2 min-w-0 flex-1 rounded-full bg-slate-200 dark:bg-slate-800">
        <motion.div
          className="h-2 rounded-full bg-indigo-500"
          initial={reduceMotion ? { width: `${pct}%` } : { width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: reduceMotion ? 0 : 0.6, ease: 'easeOut' }}
        />
      </div>
      <span className="shrink-0 font-mono text-xs text-slate-500 dark:text-slate-400">
        {formatConfidence(value)}
      </span>
    </div>
  )
}
