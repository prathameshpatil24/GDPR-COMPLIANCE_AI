import { BarChart3, ChevronLeft, ChevronRight, Clock, Search, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { SimpleTooltip } from '@/components/ui/tooltip'
import { useAnalysisCount } from '@/context/AnalysisCountContext'
import { useShellLayout } from '@/context/ShellLayoutContext'
import { APP_NAME, APP_VERSION, NAV_ITEMS } from '@/lib/constants'
import { cn } from '@/lib/utils'

const ICON_MAP = {
  Search,
  Clock,
  BarChart3,
  Settings,
}

/** Above this value the sidebar shows a capped label (matches History list limit semantics). */
const HISTORY_BADGE_CAP = 99

/**
 * Primary navigation: full width on desktop when expanded, icon rail when collapsed.
 * @param {{ className?: string }} props
 */
export default function Sidebar({ className }) {
  const { count: analysisCount } = useAnalysisCount()
  const {
    isLg,
    desktopCollapsed,
    toggleDesktopCollapsed,
    mobileOpen,
    closeMobile,
    sidebarWide,
  } = useShellLayout()

  const narrow = !sidebarWide

  const historyCountLabel =
    analysisCount != null && analysisCount > 0
      ? analysisCount > HISTORY_BADGE_CAP
        ? `${HISTORY_BADGE_CAP}+`
        : String(analysisCount)
      : null

  return (
    <>
      {!isLg && mobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          aria-label="Close menu"
          onClick={closeMobile}
        />
      ) : null}

      <aside
        className={cn(
          'fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-slate-200 bg-white transition-all duration-300 dark:border-slate-800 dark:bg-slate-950',
          sidebarWide ? 'w-64' : 'w-16',
          className
        )}
      >
        <div
          className={cn(
            'border-b border-slate-200 dark:border-slate-800',
            narrow ? 'px-2 py-4' : 'px-6 py-5'
          )}
        >
          {narrow ? (
            <div
              className="flex h-10 w-full items-center justify-center rounded-lg bg-indigo-500/10 font-mono text-sm font-bold text-indigo-600 dark:text-indigo-400"
              aria-hidden
            >
              G
            </div>
          ) : (
            <>
              <div className="text-lg font-semibold text-slate-900 dark:text-slate-50">
                <span className="text-indigo-600 dark:text-indigo-400">{APP_NAME.split(' ')[0]}</span>{' '}
                <span className="text-slate-700 dark:text-slate-200">{APP_NAME.split(' ')[1] ?? ''}</span>
              </div>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">Compliance analysis</p>
            </>
          )}
        </div>

        <nav className="flex flex-1 flex-col gap-1 p-2 lg:p-3" aria-label="Main navigation">
            {NAV_ITEMS.map((item) => {
              const Icon = ICON_MAP[item.icon] ?? Search
              const link = (
                <NavLink
                  to={item.path}
                  end={item.path === '/'}
                  onClick={() => {
                    if (!isLg) closeMobile()
                  }}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg py-2.5 text-sm font-medium transition-colors duration-150',
                      narrow ? 'relative justify-center px-2' : 'px-3',
                      isActive
                        ? 'bg-slate-200/80 text-indigo-600 dark:bg-slate-800/50 dark:text-indigo-400'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/30 dark:hover:text-slate-200'
                    )
                  }
                >
                  <Icon className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
                  {!narrow ? (
                    <>
                      <span className="flex-1">{item.label}</span>
                      {item.path === '/history' && historyCountLabel ? (
                        <span
                          className="min-w-[1.25rem] rounded-full bg-slate-200 px-1.5 text-center text-xs font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                          aria-hidden
                        >
                          {historyCountLabel}
                        </span>
                      ) : null}
                    </>
                  ) : null}
                  {narrow && item.path === '/history' && historyCountLabel ? (
                    <span
                      className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-slate-200 px-1 text-[10px] font-semibold leading-none text-slate-700 dark:bg-slate-700 dark:text-slate-200"
                      aria-label={`${analysisCount} analyses in history`}
                    >
                      {historyCountLabel}
                    </span>
                  ) : null}
                </NavLink>
              )

              if (narrow) {
                return (
                  <SimpleTooltip key={item.path} content={item.label} side="right">
                    <span className="contents">{link}</span>
                  </SimpleTooltip>
                )
              }
              return <div key={item.path}>{link}</div>
            })}
        </nav>

        <div className="mt-auto border-t border-slate-200 p-2 dark:border-slate-800 lg:p-4">
          {isLg ? (
            <button
              type="button"
              onClick={toggleDesktopCollapsed}
              className={cn(
                'flex w-full items-center justify-center rounded-lg py-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800 dark:hover:text-slate-200',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-950'
              )}
              aria-label={desktopCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {desktopCollapsed ? (
                <ChevronRight className="h-4 w-4" aria-hidden />
              ) : (
                <ChevronLeft className="h-4 w-4" aria-hidden />
              )}
            </button>
          ) : null}
          {!narrow ? (
            <p className="mt-2 text-center text-xs text-slate-500 dark:text-slate-600 lg:text-left">
              UI v{APP_VERSION}
            </p>
          ) : null}
        </div>
      </aside>
    </>
  )
}
