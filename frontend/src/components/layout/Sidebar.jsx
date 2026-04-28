import { BarChart3, Clock, Search, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { useNavMetrics } from '@/context/NavMetricsContext'
import { APP_NAME, APP_VERSION, NAV_ITEMS } from '@/lib/constants'
import { cn } from '@/lib/utils'

const ICON_MAP = {
  Search,
  Clock,
  BarChart3,
  Settings,
}

/**
 * Fixed left navigation for primary routes.
 * @param {{ className?: string }} props
 */
export default function Sidebar({ className }) {
  const { totalQueries } = useNavMetrics()

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-screen w-64 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950',
        className
      )}
    >
      <div className="border-b border-slate-200 px-6 py-5 dark:border-slate-800">
        <div className="text-lg font-semibold text-slate-900 dark:text-slate-50">
          <span className="text-indigo-600 dark:text-indigo-400">{APP_NAME.split(' ')[0]}</span>{' '}
          <span className="text-slate-700 dark:text-slate-200">{APP_NAME.split(' ')[1] ?? ''}</span>
        </div>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">Compliance analysis</p>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {NAV_ITEMS.map((item) => {
          const Icon = ICON_MAP[item.icon] ?? Search
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                cn(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-slate-200/80 text-indigo-600 dark:bg-slate-800/50 dark:text-indigo-400'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/30 dark:hover:text-slate-200'
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
              <span className="flex-1">{item.label}</span>
              {item.path === '/history' &&
              totalQueries != null &&
              totalQueries > 0 ? (
                <span className="min-w-[1.25rem] rounded-full bg-slate-200 px-1.5 text-center text-xs font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                  {totalQueries > 99 ? '99+' : totalQueries}
                </span>
              ) : null}
            </NavLink>
          )
        })}
      </nav>
      <div className="mt-auto border-t border-slate-200 p-4 dark:border-slate-800">
        <p className="text-xs text-slate-500 dark:text-slate-600">UI v{APP_VERSION}</p>
      </div>
    </aside>
  )
}
