import { useLocation } from 'react-router-dom'

import { Switch } from '@/components/ui/switch'
import { useTheme } from '@/context/ThemeContext'
import { cn } from '@/lib/utils'

const TITLES = {
  '/': 'Analyze',
  '/history': 'History',
  '/stats': 'Dashboard',
  '/settings': 'Settings',
}

/**
 * Top bar: page title and theme switch (dark = checked).
 * @param {{ health?: { ok?: boolean; version?: string } | null, className?: string }} props
 */
export default function Header({ health = null, className }) {
  const location = useLocation()
  const title = TITLES[location.pathname] ?? 'GDPR AI'
  const { isDark, setIsDark } = useTheme()

  return (
    <header
      className={cn(
        'flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white/80 px-6 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/80',
        className
      )}
    >
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold text-slate-900 dark:text-slate-50">{title}</h1>
        {health?.ok === true && health.version ? (
          <span className="hidden font-mono text-xs text-slate-500 dark:text-slate-500 sm:inline">
            API {health.version}
          </span>
        ) : null}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-slate-500 dark:text-slate-400">Dark</span>
        <Switch checked={isDark} onCheckedChange={setIsDark} aria-label="Toggle dark mode" />
      </div>
    </header>
  )
}
