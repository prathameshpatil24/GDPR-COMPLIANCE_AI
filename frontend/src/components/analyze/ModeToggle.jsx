import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'

import { MODES } from '@/lib/constants'
import { cn } from '@/lib/utils'

const TABS = [
  { id: MODES.VIOLATION, label: 'Violation Analysis' },
  { id: MODES.COMPLIANCE, label: 'Compliance Assessment' },
]

/**
 * Segmented control for analyze mode with sliding highlight.
 * @param {{ value: string, onChange: (id: string) => void, disabled?: boolean }} props
 */
export default function ModeToggle({ value, onChange, disabled = false }) {
  const reduceMotion = useReducedMotion()

  return (
    <div
      className="inline-flex rounded-lg bg-slate-200/80 p-1 dark:bg-slate-800/50"
      role="tablist"
      aria-label="Analysis mode"
    >
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={value === tab.id}
          disabled={disabled}
          onClick={() => onChange(tab.id)}
          className={cn(
            'relative min-w-[10rem] flex-1 rounded-md px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-50 sm:min-w-[12rem]',
            value === tab.id
              ? 'text-indigo-600 dark:text-indigo-400'
              : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
          )}
        >
          {value === tab.id ? (
            <motion.div
              layoutId={reduceMotion ? undefined : 'mode-indicator'}
              className="absolute inset-0 rounded-md bg-indigo-500/10"
              transition={
                reduceMotion
                  ? { duration: 0 }
                  : { type: 'spring', stiffness: 500, damping: 30 }
              }
            />
          ) : null}
          <span className="relative z-10">{tab.label}</span>
        </button>
      ))}
    </div>
  )
}
