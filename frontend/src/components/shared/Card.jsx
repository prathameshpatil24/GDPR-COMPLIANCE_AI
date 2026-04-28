import { cn } from '@/lib/utils'

/**
 * Surface card following v3 design system.
 * @param {{ children: import('react').ReactNode, className?: string }} props
 */
export default function Card({ children, className }) {
  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 bg-slate-50 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:shadow-none',
        className
      )}
    >
      {children}
    </div>
  )
}
