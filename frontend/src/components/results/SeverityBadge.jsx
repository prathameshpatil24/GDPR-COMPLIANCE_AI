import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { severityConfig } from '@/lib/theme'
import { cn } from '@/lib/utils'

/**
 * Violation severity or compliance risk level pill with optional pulse (critical only).
 * @param {{ level: string, className?: string }} props
 */
export default function SeverityBadge({ level, className }) {
  const key = String(level || 'unknown').toLowerCase()
  const conf = severityConfig[key] ?? severityConfig.unknown
  const reduceMotion = useReducedMotion()
  const pulse = key === 'critical' && conf.pulse && !reduceMotion

  const inner = (
    <span
      className={cn(
        'inline-flex rounded-full px-3 py-1 text-xs font-medium',
        conf.bg,
        conf.color,
        className
      )}
      aria-label={`Severity: ${conf.label}`}
    >
      {conf.label}
    </span>
  )

  if (!pulse) return inner

  return (
    <motion.span
      animate={{ opacity: [0.7, 1], scale: [0.98, 1] }}
      transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
      className="inline-flex"
    >
      {inner}
    </motion.span>
  )
}
