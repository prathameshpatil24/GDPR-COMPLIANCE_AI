import { useCallback, useEffect, useState } from 'react'

import { useDebug } from '@/context/DebugContext'

import { Activity, Moon, Sun } from 'lucide-react'
import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'

import { getStats, healthCheck } from '@/api/client'
import Card from '@/components/shared/Card'
import Skeleton from '@/components/shared/Skeleton'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { useTheme } from '@/context/ThemeContext'
import {
  APP_NAME,
  APP_VERSION,
  AUTHOR_NAME,
  BACKEND_URL_DISPLAY,
  DEFAULT_APP_DB_PATH,
  GITHUB_REPO_URL,
} from '@/lib/constants'

/**
 * Theme, connection, data summary, and about.
 */
export default function SettingsPage() {
  const { isDark, setIsDark } = useTheme()
  const { debugMode, unlock, lock } = useDebug()
  const reduceMotionFramer = useReducedMotion()
  const [debugCode, setDebugCode] = useState('')
  const [invalidCode, setInvalidCode] = useState(false)
  const [health, setHealth] = useState(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [totalQueries, setTotalQueries] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)

  const probeHealth = useCallback(() => {
    setHealthLoading(true)
    healthCheck()
      .then((r) => setHealth({ ok: true, ...r.data }))
      .catch(() => setHealth({ ok: false }))
      .finally(() => setHealthLoading(false))
  }, [])

  const loadStats = useCallback(() => {
    setStatsLoading(true)
    getStats()
      .then((r) => setTotalQueries(Number(r.data?.total_queries ?? 0)))
      .catch(() => setTotalQueries(null))
      .finally(() => setStatsLoading(false))
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => {
      probeHealth()
      loadStats()
    }, 0)
    return () => window.clearTimeout(id)
  }, [probeHealth, loadStats])

  useEffect(() => {
    if (!invalidCode) return undefined
    const t = window.setTimeout(() => setInvalidCode(false), 2000)
    return () => window.clearTimeout(t)
  }, [invalidCode])

  const tryUnlockDebug = () => {
    const trimmed = debugCode.trim()
    if (!trimmed) return
    if (unlock(trimmed)) {
      setDebugCode('')
      setInvalidCode(false)
    } else {
      setInvalidCode(true)
    }
  }

  const cardMotion = (i) => ({
    initial: reduceMotionFramer ? false : { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: reduceMotionFramer ? 0 : 0.35, delay: reduceMotionFramer ? 0 : i * 0.08 },
  })

  const showSkeleton = healthLoading || statsLoading

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Settings</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Appearance, API connectivity, and product information.
        </p>
      </div>

      {showSkeleton ? (
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      ) : (
        <>
          <motion.section {...cardMotion(0)}>
            <Card className="border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-4 text-lg font-medium text-slate-900 dark:text-slate-50">Appearance</h2>
              <div className="flex flex-wrap items-center gap-4">
                <Sun className="h-5 w-5 text-amber-500" aria-hidden />
                <Switch
                  checked={isDark}
                  onCheckedChange={setIsDark}
                  aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
                />
                <Moon className="h-5 w-5 text-slate-400" aria-hidden />
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  {isDark ? 'Dark theme' : 'Light theme'}
                </span>
              </div>
            </Card>
          </motion.section>

          <motion.section {...cardMotion(1)}>
            <Card className="border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-4 text-lg font-medium text-slate-900 dark:text-slate-50">Connection</h2>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Backend URL:{' '}
                <span className="font-mono text-slate-800 dark:text-slate-200">{BACKEND_URL_DISPLAY}</span>
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {healthLoading ? (
                  <span className="text-sm text-slate-500">Checking…</span>
                ) : health?.ok ? (
                  <>
                    <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" aria-hidden />
                    <span className="text-sm font-medium text-emerald-600 dark:text-emerald-500">
                      Connected
                      {health.version ? ` (v${health.version})` : ''}
                    </span>
                  </>
                ) : (
                  <>
                    <span className="inline-block h-2 w-2 rounded-full bg-rose-500" aria-hidden />
                    <span className="text-sm font-medium text-rose-600 dark:text-rose-500">
                      Disconnected
                    </span>
                  </>
                )}
              </div>
              <Button
                type="button"
                variant="secondary"
                className="mt-4"
                onClick={() => probeHealth()}
                disabled={healthLoading}
              >
                Test connection
              </Button>
            </Card>
          </motion.section>

          <motion.section {...cardMotion(2)}>
            <Card className="border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-4 text-lg font-medium text-slate-900 dark:text-slate-50">Data</h2>
              <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
                <li className="flex items-center gap-2">
                  <Activity className="h-4 w-4 shrink-0 text-slate-500" aria-hidden />
                  Total analyses (query log):{' '}
                  <span className="font-mono text-slate-900 dark:text-slate-200">
                    {statsLoading ? '…' : totalQueries ?? '—'}
                  </span>
                </li>
                <li>
                  Database:{' '}
                  <span className="font-mono text-slate-800 dark:text-slate-200">{DEFAULT_APP_DB_PATH}</span>{' '}
                  <span className="text-slate-500">(default path; local SQLite)</span>
                </li>
              </ul>
            </Card>
          </motion.section>

          <motion.section {...cardMotion(3)}>
            <Card className="border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-4 text-lg font-medium text-slate-900 dark:text-slate-50">Developer</h2>
              <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
                Optional debug visibility for internal identifiers (e.g. retrieval chunk IDs). Nothing is
                stored in the browser; closing or refreshing the page turns this off.
              </p>
              {!debugMode ? (
                <div className="space-y-3">
                  <label className="block text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500">
                    Debug access code
                  </label>
                  <input
                    type="password"
                    value={debugCode}
                    onChange={(e) => setDebugCode(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') tryUnlockDebug()
                    }}
                    autoComplete="off"
                    className="h-10 w-full max-w-sm rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500"
                    placeholder="Enter code"
                  />
                  {invalidCode ? (
                    <p className="text-sm text-rose-600 dark:text-rose-400" role="alert">
                      Invalid code
                    </p>
                  ) : null}
                  <Button type="button" onClick={tryUnlockDebug}>
                    Unlock
                  </Button>
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-3">
                  <span className="inline-flex items-center gap-2 rounded-full bg-emerald-500/15 px-3 py-1 text-sm font-medium text-emerald-700 dark:text-emerald-400">
                    <span className="h-2 w-2 rounded-full bg-emerald-500" aria-hidden />
                    Debug mode enabled
                  </span>
                  <Button type="button" variant="secondary" onClick={() => lock()}>
                    Lock
                  </Button>
                </div>
              )}
            </Card>
          </motion.section>

          <motion.section {...cardMotion(4)}>
            <Card className="border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <h2 className="mb-4 text-lg font-medium text-slate-900 dark:text-slate-50">About</h2>
              <p className="text-sm text-slate-700 dark:text-slate-300">
                {APP_NAME} UI v{APP_VERSION}
              </p>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                Backend version is shown when connected (from{' '}
                <span className="font-mono">/health</span>).
              </p>
              <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">
                Built by {AUTHOR_NAME}.{' '}
                <a
                  href={GITHUB_REPO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
                >
                  {GITHUB_REPO_URL.replace('https://', '')}
                </a>
              </p>
              <p className="mt-6 text-xs italic text-slate-500 dark:text-slate-500">
                Informational only; not legal advice.
              </p>
            </Card>
          </motion.section>
        </>
      )}
    </div>
  )
}
