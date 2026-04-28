import { statusConfig } from '@/lib/theme'
import { cn } from '@/lib/utils'

/**
 * Compliance finding status pill (static).
 * @param {{ status: string, className?: string }} props
 */
export default function StatusBadge({ status, className }) {
  const key = String(status || '')
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '_')
    .replace(/-/g, '_')
  const conf = statusConfig[key] ?? statusConfig.insufficient_info

  return (
    <span
      className={cn(
        'inline-flex rounded-full px-3 py-1 text-xs font-medium',
        conf.bg,
        conf.color,
        className
      )}
      aria-label={`Finding status: ${conf.label}`}
    >
      {conf.label}
    </span>
  )
}
