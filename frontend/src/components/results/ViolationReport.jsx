import * as Collapsible from '@radix-ui/react-collapsible'
import { ChevronDown } from 'lucide-react'
import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useState } from 'react'

import ArticleTag from '@/components/results/ArticleTag'
import CitationList from '@/components/results/CitationList'
import ConfidenceBar from '@/components/results/ConfidenceBar'
import RecommendationList from '@/components/results/RecommendationList'
import RetrievalGapNote from '@/components/results/RetrievalGapNote'
import SeverityBadge from '@/components/results/SeverityBadge'
import { useDebug } from '@/context/DebugContext'
import { cn } from '@/lib/utils'

/**
 * Full violation analysis report from API `result` object.
 * @param {{ analysisId: string, result: object, completedAt?: string | null }} props
 */
export default function ViolationReport({ analysisId, result, completedAt }) {
  const reduceMotion = useReducedMotion()
  const violations = result.violations || []
  const ts =
    completedAt != null && completedAt !== ''
      ? new Date(completedAt).toLocaleString()
      : null

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <SeverityBadge level={result.severity_level} />
          <p className="font-mono text-xs text-slate-500 dark:text-slate-500">{analysisId}</p>
          {ts ? <p className="text-sm text-slate-600 dark:text-slate-400">{ts}</p> : null}
        </div>
      </header>

      <motion.section
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="rounded-xl border border-slate-200 bg-slate-100/80 p-6 dark:border-slate-800 dark:bg-slate-800/50"
      >
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500">
          Summary
        </h2>
        <p className="text-sm leading-relaxed text-slate-800 dark:text-slate-200">
          {result.scenario_summary}
        </p>
      </motion.section>

      <section>
        <h2 className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-50">
          Violations ({violations.length})
        </h2>
        <ul className="space-y-3">
          {violations.map((v, index) => (
            <ViolationCard key={`${v.article_reference}-${index}`} violation={v} index={index} />
          ))}
        </ul>
      </section>

      {result.recommendations?.length ? (
        <section>
          <h2 className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-50">
            Recommendations
          </h2>
          <RecommendationList items={result.recommendations} />
        </section>
      ) : null}

      <RetrievalGapNote notes={result.unsupported_notes} />

      {result.citations?.length ? (
        <section>
          <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-slate-50">Citations</h2>
          <CitationList items={result.citations} />
        </section>
      ) : null}

      <p className="text-xs italic text-slate-500 dark:text-slate-600">
        Informational only; not legal advice.
      </p>
    </div>
  )
}

/**
 * @param {{ violation: object, index: number }} props
 */
function ViolationCard({ violation, index }) {
  const [open, setOpen] = useState(false)
  const reduceMotion = useReducedMotion()
  const { debugMode } = useDebug()
  const ids = violation.supporting_chunk_ids || []
  const url = violation.source_url?.trim()

  return (
    <motion.li
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: reduceMotion ? 0 : index * 0.06, duration: 0.35 }}
    >
      <Collapsible.Root open={open} onOpenChange={setOpen}>
        <div className="rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
          <Collapsible.Trigger
            type="button"
            className="flex w-full cursor-pointer items-center gap-3 rounded-xl p-4 text-left transition-colors hover:bg-slate-100/80 dark:hover:bg-slate-800/40"
          >
            <ArticleTag label={violation.article_reference} className="shrink-0" />
            <div className="min-w-0 flex-1">
              <ConfidenceBar value={violation.confidence} />
            </div>
            <ChevronDown
              className={cn('h-5 w-5 shrink-0 text-slate-500 transition-transform', open && 'rotate-180')}
              aria-hidden
            />
          </Collapsible.Trigger>
          <Collapsible.Content className="border-t border-slate-200 dark:border-slate-800">
            <div className="space-y-4 px-4 pb-4 pt-3 text-sm">
              <p className="leading-relaxed text-slate-700 dark:text-slate-300">{violation.description}</p>
              {debugMode && ids.length ? (
                <div>
                  <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500">
                    Supporting chunk IDs
                  </h4>
                  <p className="font-mono text-xs text-slate-600 dark:text-slate-400">{ids.join(', ')}</p>
                </div>
              ) : null}
              {url ? (
                <div>
                  <h4 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500">
                    Source
                  </h4>
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="break-all text-indigo-600 underline decoration-indigo-500/40 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
                  >
                    {url}
                  </a>
                </div>
              ) : null}
            </div>
          </Collapsible.Content>
        </div>
      </Collapsible.Root>
    </motion.li>
  )
}
