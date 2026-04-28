import { useLayoutEffect, useRef } from 'react'

import { MODES, PLACEHOLDERS } from '@/lib/constants'
import { cn } from '@/lib/utils'

const MAX_AUTO_HEIGHT = 480
const MIN_HEIGHT = 120

/**
 * Large textarea for scenario or system description (auto-growing height).
 * @param {{ value: string, onChange: (s: string) => void, mode: string, maxLength: number, disabled?: boolean, className?: string }} props
 */
export default function ScenarioInput({ value, onChange, mode, maxLength, disabled = false, className }) {
  const placeholder = PLACEHOLDERS[mode] ?? PLACEHOLDERS[MODES.VIOLATION]
  const len = value.length
  const ref = useRef(null)

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    const next = Math.min(Math.max(el.scrollHeight, MIN_HEIGHT), MAX_AUTO_HEIGHT)
    el.style.height = `${next}px`
  }, [value, mode])

  return (
    <div className={cn('relative', className)}>
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        maxLength={maxLength}
        placeholder={placeholder}
        rows={6}
        className="min-h-[120px] w-full resize-y rounded-xl border border-slate-300 bg-white p-4 text-sm leading-relaxed text-slate-900 transition-[height] duration-150 ease-out placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 sm:min-h-[160px] dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-indigo-500"
      />
      <div className="pointer-events-none absolute bottom-3 right-3 text-xs text-slate-500 dark:text-slate-500">
        {len.toLocaleString()} / {maxLength.toLocaleString()}
      </div>
    </div>
  )
}
