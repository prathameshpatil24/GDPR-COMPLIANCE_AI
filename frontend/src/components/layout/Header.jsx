import { Menu, Moon, Sun } from 'lucide-react'
import { useLocation } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { useShellLayout } from '@/context/ShellLayoutContext'
import { useTheme } from '@/context/ThemeContext'
import { cn } from '@/lib/utils'

const TITLES = {
  '/': 'Analyze',
  '/history': 'History',
  '/stats': 'Dashboard',
  '/settings': 'Settings',
}

/**
 * Top bar: page title, mobile menu, theme switch.
 * @param {{ health?: { ok?: boolean; version?: string } | null, className?: string }} props
 */
export default function Header({ health = null, className }) {
  const location = useLocation()
  const title = TITLES[location.pathname] ?? 'GDPR AI'
  const { isDark, setIsDark } = useTheme()
  const { isLg, toggleMobile } = useShellLayout()

  return (
    <header
      className={cn(
        'flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white/80 px-4 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/80 lg:px-6',
        className
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        {!isLg ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="shrink-0 lg:hidden"
            onClick={toggleMobile}
            aria-label="Open navigation menu"
          >
            <Menu className="h-5 w-5" aria-hidden />
          </Button>
        ) : null}
        <h1 className="truncate text-base font-semibold text-slate-900 dark:text-slate-50">{title}</h1>
        {health?.ok === true && health.version ? (
          <span className="hidden font-mono text-xs text-slate-500 dark:text-slate-500 sm:inline">
            API {health.version}
          </span>
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        {isDark ? (
          <Moon className="hidden h-4 w-4 text-slate-500 sm:block" aria-hidden />
        ) : (
          <Sun className="hidden h-4 w-4 text-amber-500 sm:block" aria-hidden />
        )}
        <span className="hidden text-xs text-slate-600 dark:text-slate-400 sm:inline">
          {isDark ? 'Dark' : 'Light'}
        </span>
        <Switch checked={isDark} onCheckedChange={setIsDark} aria-label="Toggle dark mode" />
      </div>
    </header>
  )
}
