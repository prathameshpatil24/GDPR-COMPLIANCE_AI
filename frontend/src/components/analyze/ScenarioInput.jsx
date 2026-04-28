import { MODES, PLACEHOLDERS } from '@/lib/constants'
import { cn } from '@/lib/utils'

/**
 * Large textarea for scenario or system description.
 * @param {{ value: string, onChange: (s: string) => void, mode: string, maxLength: number, disabled?: boolean, className?: string }} props
 */
export default function ScenarioInput({ value, onChange, mode, maxLength, disabled = false, className }) {
  const placeholder = PLACEHOLDERS[mode] ?? PLACEHOLDERS[MODES.VIOLATION]
  const len = value.length

  return (
    <div className={cn('relative', className)}>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        maxLength={maxLength}
        placeholder={placeholder}
        rows={8}
        className="min-h-[160px] w-full resize-y rounded-xl border border-slate-300 bg-white p-4 text-sm leading-relaxed text-slate-900 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-indigo-500"
      />
      <div className="pointer-events-none absolute bottom-3 right-3 text-xs text-slate-500 dark:text-slate-500">
        {len.toLocaleString()} / {maxLength.toLocaleString()}
      </div>
    </div>
  )
}
