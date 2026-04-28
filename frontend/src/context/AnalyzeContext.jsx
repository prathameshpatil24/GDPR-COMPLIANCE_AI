/* eslint-disable react-refresh/only-export-components -- Provider + hooks */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { analyzeCompliance, analyzeViolation, getErrorMessage } from '@/api/client'
import { MODES } from '@/lib/constants'

const AnalyzeContext = createContext(
  /** @type {null | {
   *   mode: string,
   *   setMode: (m: string) => void,
   *   inputText: string,
   *   setInputText: (t: string) => void,
   *   result: object | null,
   *   loading: boolean,
   *   error: string | null,
   *   elapsedSec: number,
   *   completedAt: string | null,
   *   analyze: (mode: string, text: string) => Promise<void>,
   *   clear: () => void,
   *   clearAnalysisState: () => void,
   * }} */ (null)
)

/**
 * Session-persistent analyze form + results (survives route changes).
 * @param {{ children: import('react').ReactNode }} props
 */
export function AnalyzeProvider({ children }) {
  const [mode, setMode] = useState(MODES.VIOLATION)
  const [inputText, setInputText] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [elapsedSec, setElapsedSec] = useState(0)
  const [completedAt, setCompletedAt] = useState(null)

  useEffect(() => {
    if (!loading) return undefined
    const t0 = Date.now()
    const id = window.setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - t0) / 1000))
    }, 1000)
    return () => window.clearInterval(id)
  }, [loading])

  const clearAnalysisState = useCallback(() => {
    setResult(null)
    setError(null)
    setCompletedAt(null)
    setElapsedSec(0)
  }, [])

  const analyze = useCallback(async (modeArg, text) => {
    setElapsedSec(0)
    setLoading(true)
    setError(null)
    setResult(null)
    setCompletedAt(null)
    try {
      const response =
        modeArg === MODES.VIOLATION
          ? await analyzeViolation(text)
          : await analyzeCompliance(text)
      setResult(response.data)
      setCompletedAt(new Date().toISOString())
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  const clear = useCallback(() => {
    clearAnalysisState()
    setInputText('')
  }, [clearAnalysisState])

  const value = useMemo(
    () => ({
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
    }),
    [
      mode,
      inputText,
      result,
      loading,
      error,
      elapsedSec,
      completedAt,
      analyze,
      clear,
      clearAnalysisState,
    ]
  )

  return <AnalyzeContext.Provider value={value}>{children}</AnalyzeContext.Provider>
}

export function useAnalyzeContext() {
  const ctx = useContext(AnalyzeContext)
  if (!ctx) throw new Error('useAnalyzeContext must be used within AnalyzeProvider')
  return ctx
}
