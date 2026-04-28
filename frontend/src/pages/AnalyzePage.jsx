import { AnimatePresence, motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useCallback, useEffect, useRef } from 'react'

import ModeToggle from '@/components/analyze/ModeToggle'
import ScenarioInput from '@/components/analyze/ScenarioInput'
import SubmitButton from '@/components/analyze/SubmitButton'
import LoadingState from '@/components/analyze/LoadingState'
import ComplianceReport from '@/components/results/ComplianceReport'
import ViolationReport from '@/components/results/ViolationReport'
import { Button } from '@/components/ui/button'
import { useAnalysisCount } from '@/context/AnalysisCountContext'
import { useAnalyzeContext } from '@/context/AnalyzeContext'
import { useToast } from '@/context/ToastContext'
import { MODES } from '@/lib/constants'

const MAX_VIOLATION = 8000
const MAX_COMPLIANCE = 32000
const MIN_VIOLATION = 10

/**
 * Analyze home: mode toggle, input, API-backed reports for violation and compliance.
 */
export default function AnalyzePage() {
  const {
    mode,
    setMode,
    inputText,
    setInputText,
    result,
    loading,
    error,
    elapsedSec,
    completedAt,
    analyze,
    clear,
    clearAnalysisState,
  } = useAnalyzeContext()
  const { showToast } = useToast()
  const { refresh: refreshAnalysisCount, increment: bumpAnalysisCount } = useAnalysisCount()
  const resultsRef = useRef(null)
  const lastToastedAnalysisId = useRef(null)
  const reduceMotion = useReducedMotion()

  const maxLength = mode === MODES.VIOLATION ? MAX_VIOLATION : MAX_COMPLIANCE
  const trimmed = inputText.trim()
  const canSubmit =
    mode === MODES.VIOLATION ? trimmed.length >= MIN_VIOLATION : trimmed.length > 0

  const handleSubmit = () => {
    if (!canSubmit || loading) return
    analyze(mode, trimmed)
  }

  const handleClear = () => {
    clear()
  }

  const handleModeChange = useCallback(
    (newMode) => {
      if (newMode === mode) return
      setMode(newMode)
      setInputText('')
      clearAnalysisState()
    },
    [mode, setMode, setInputText, clearAnalysisState]
  )

  useEffect(() => {
    const id = result?.analysis_id
    if (id && id !== lastToastedAnalysisId.current) {
      lastToastedAnalysisId.current = id
      showToast({ type: 'success', message: 'Analysis complete' })
      bumpAnalysisCount()
      void refreshAnalysisCount()
      window.setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 100)
    }
    if (!result) {
      lastToastedAnalysisId.current = null
    }
  }, [result, showToast, bumpAnalysisCount, refreshAnalysisCount])

  useEffect(() => {
    if (error) {
      showToast({ type: 'error', message: error })
    }
  }, [error, showToast])

  const innerResult = result?.result
  const analysisId = result?.analysis_id ?? ''
  const resultMode = result?.mode

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
        Run violation analysis or a compliance assessment against your local GDPR AI API. Results appear
        below when the run finishes.
      </p>
      <ModeToggle value={mode} onChange={handleModeChange} disabled={loading} />
      <ScenarioInput
        value={inputText}
        onChange={setInputText}
        mode={mode}
        maxLength={maxLength}
        disabled={loading}
      />
      <div className="flex flex-wrap items-center justify-end gap-3">
        <Button type="button" variant="ghost" disabled={loading} onClick={handleClear}>
          Clear
        </Button>
        <SubmitButton onClick={handleSubmit} loading={loading} disabled={!canSubmit} />
      </div>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-700 dark:text-rose-400"
        >
          {error}
        </div>
      ) : null}

      {loading ? <LoadingState key={mode} mode={mode} elapsedSec={elapsedSec} /> : null}

      <div ref={resultsRef}>
        <AnimatePresence mode="wait">
          {!loading && innerResult && resultMode === 'violation_analysis' ? (
            <motion.div
              key={`v-${analysisId}`}
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? undefined : { opacity: 0, y: -8 }}
              transition={{ duration: reduceMotion ? 0 : 0.25 }}
              className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950/40"
            >
              <ViolationReport analysisId={analysisId} result={innerResult} completedAt={completedAt} />
            </motion.div>
          ) : !loading && innerResult && resultMode === 'compliance_assessment' ? (
            <motion.div
              key={`c-${analysisId}`}
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? undefined : { opacity: 0, y: -8 }}
              transition={{ duration: reduceMotion ? 0 : 0.25 }}
              className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950/40"
            >
              <ComplianceReport analysisId={analysisId} result={innerResult} completedAt={completedAt} />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  )
}
