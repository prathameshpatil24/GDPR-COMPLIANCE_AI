import { cn } from '@/lib/utils'

/**
 * Centered empty state with optional icon and action.
 * @param {{ icon?: import('react').ReactNode, title: string, description?: string, action?: import('react').ReactNode, className?: string }} props
 */
export default function EmptyState({ icon, title, description, action, className }) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 py-16 text-center dark:border-slate-700',
        className
      )}
    >
      {icon ? <div className="text-slate-400 dark:text-slate-500">{icon}</div> : null}
      <h2 className="text-base font-semibold text-slate-700 dark:text-slate-300">{title}</h2>
      {description ? <p className="max-w-md text-sm text-slate-500 dark:text-slate-500">{description}</p> : null}
      {action}
    </div>
  )
}
