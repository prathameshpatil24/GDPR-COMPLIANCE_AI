import { useState } from 'react'

import { healthCheck } from '@/api/client'
import Card from '@/components/shared/Card'
import { Switch } from '@/components/ui/switch'
import { APP_NAME, APP_VERSION } from '@/lib/constants'
import { useTheme } from '@/context/ThemeContext'

/**
 * Configuration and about.
 */
export default function SettingsPage() {
  const { isDark, setIsDark } = useTheme()
  const [apiKey, setApiKey] = useState('')
  const [health, setHealth] = useState(null)

  const probeHealth = () => {
    healthCheck()
      .then((r) => setHealth({ ok: true, ...r.data }))
      .catch(() => setHealth({ ok: false }))
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Card>
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-50">Anthropic API key</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Local runs use the key from the FastAPI server <span className="font-mono">.env</span> (
          <span className="font-mono">ANTHROPIC_API_KEY</span>). This field is optional placeholder UI for
          future BYOK flows.
        </p>
        <input
          type="password"
          autoComplete="off"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Not sent to the server in v3 M1"
          className="mt-4 w-full max-w-md rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-100"
        />
      </Card>

      <Card>
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-50">Appearance</h2>
        <div className="mt-4 flex items-center gap-3">
          <span className="text-sm text-slate-600 dark:text-slate-400">Dark mode</span>
          <Switch checked={isDark} onCheckedChange={setIsDark} aria-label="Dark mode" />
        </div>
      </Card>

      <Card>
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-50">About</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          {APP_NAME} — UI {APP_VERSION} (Milestone 1 scaffold)
        </p>
        <button
          type="button"
          onClick={probeHealth}
          className="mt-4 text-sm font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
        >
          Check API health
        </button>
        {health ? (
          <p className="mt-2 font-mono text-xs text-slate-500 dark:text-slate-500">
            {health.ok ? `status=${health.status} version=${health.version}` : 'unreachable'}
          </p>
        ) : null}
      </Card>
    </div>
  )
}
