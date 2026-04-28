import { useState } from 'react'

import ModeToggle from '@/components/analyze/ModeToggle'
import ScenarioInput from '@/components/analyze/ScenarioInput'
import SubmitButton from '@/components/analyze/SubmitButton'
import { MODES } from '@/lib/constants'

const MAX_VIOLATION = 8000
const MAX_COMPLIANCE = 32000
const MIN_VIOLATION = 10

/**
 * Analyze home: mode toggle, input, submit (loading only until Milestone 2).
 */
export default function AnalyzePage() {
  const [mode, setMode] = useState(MODES.VIOLATION)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)

  const maxLength = mode === MODES.VIOLATION ? MAX_VIOLATION : MAX_COMPLIANCE
  const trimmed = text.trim()
  const canSubmit =
    mode === MODES.VIOLATION ? trimmed.length >= MIN_VIOLATION : trimmed.length > 0

  const handleSubmit = () => {
    if (!canSubmit || loading) return
    setLoading(true)
    window.setTimeout(() => setLoading(false), 2000)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
        Run violation analysis or a compliance assessment against your local GDPR AI API. Full results
        rendering ships in Milestone 2.
      </p>
      <ModeToggle value={mode} onChange={setMode} disabled={loading} />
      <ScenarioInput
        value={text}
        onChange={setText}
        mode={mode}
        maxLength={maxLength}
        disabled={loading}
      />
      <div className="flex justify-end">
        <SubmitButton onClick={handleSubmit} loading={loading} disabled={!canSubmit} />
      </div>
    </div>
  )
}
