import { Check, Loader2 } from 'lucide-react'
import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useEffect, useMemo, useState } from 'react'

import { MODES } from '@/lib/constants'
import Skeleton from '@/components/shared/Skeleton'

const VIOLATION_STAGES = [
  'Extracting entities…',
  'Classifying topics…',
  'Retrieving relevant articles…',
  'Reasoning over violations…',
  'Validating citations…',
]

const COMPLIANCE_STAGES = [
  'Extracting entities…',
  'Classifying topics…',
  'Retrieving relevant articles…',
  'Analyzing compliance…',
  'Validating citations…',
]

/**
 * Long-running analysis UX: timer, estimates, skeletons, faux pipeline stages.
 * @param {{ mode: string, elapsedSec: number }} props
 */
export default function LoadingState({ mode, elapsedSec }) {
  const reduceMotion = useReducedMotion()
  const stages = mode === MODES.COMPLIANCE ? COMPLIANCE_STAGES : VIOLATION_STAGES
  const [activeIdx, setActiveIdx] = useState(0)

  useEffect(() => {
    const stepMs = 20000
    const id = window.setInterval(() => {
      setActiveIdx((i) => Math.min(i + 1, stages.length - 1))
    }, stepMs)
    return () => window.clearInterval(id)
  }, [stages.length])

  const estimate = useMemo(
    () =>
      mode === MODES.COMPLIANCE
        ? 'Compliance assessments typically take 60–190 seconds'
        : 'Violation analyses typically take 20–120 seconds',
    [mode]
  )

  return (
    <div
      className="space-y-6 rounded-xl border border-slate-200 bg-slate-50/80 p-8 dark:border-slate-800 dark:bg-slate-900/50"
      aria-live="polite"
      aria-busy="true"
    >
      <div
        className="h-1 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
        aria-hidden
      >
        <motion.div
          className="h-full w-1/3 bg-indigo-500"
          animate={reduceMotion ? {} : { x: ['-100%', '400%'] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
        />
      </div>

      <div>
        <p className="font-mono text-2xl font-semibold text-slate-900 dark:text-slate-50">
          Analyzing… {elapsedSec}s
        </p>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{estimate}</p>
      </div>

      <ul className="space-y-3">
        {stages.map((label, i) => {
          const done = i < activeIdx
          const active = i === activeIdx
          return (
            <li
              key={label}
              className={`flex items-center gap-3 text-sm ${
                done
                  ? 'text-emerald-600 dark:text-emerald-500'
                  : active
                    ? 'text-indigo-600 dark:text-indigo-400'
                    : 'text-slate-500 dark:text-slate-600'
              }`}
            >
              {done ? (
                <motion.span
                  initial={reduceMotion ? false : { scale: 0 }}
                  animate={{ scale: 1 }}
                  className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/15"
                >
                  <Check className="h-4 w-4" aria-hidden />
                </motion.span>
              ) : active ? (
                <Loader2 className="h-5 w-5 shrink-0 animate-spin text-indigo-500" aria-hidden />
              ) : (
                <span className="h-5 w-5 shrink-0 rounded-full border border-slate-600" />
              )}
              {label}
            </li>
          )
        })}
      </ul>

      <div className="space-y-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
    </div>
  )
}
