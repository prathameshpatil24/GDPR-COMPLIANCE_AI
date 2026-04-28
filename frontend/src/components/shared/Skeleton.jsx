import { cn } from '@/lib/utils'

/**
 * Loading placeholder with pulse.
 * @param {{ className?: string }} props
 */
export default function Skeleton({ className }) {
  return <div className={cn('animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800', className)} aria-hidden />
}
