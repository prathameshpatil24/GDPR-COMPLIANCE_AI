import { severityConfig, statusConfig } from '@/lib/theme'
import { cn } from '@/lib/utils'

/**
 * Pill badge for severity or compliance status.
 * @param {{ variant: string, type?: 'severity' | 'status', className?: string, children?: import('react').ReactNode }} props
 */
export default function Badge({ variant, type = 'severity', className, children }) {
  const conf =
    type === 'status'
      ? statusConfig[variant] ?? statusConfig.insufficient_info
      : severityConfig[variant] ?? severityConfig.unknown

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
        conf.bg,
        conf.color,
        className
      )}
    >
      {children ?? conf.label}
    </span>
  )
}
