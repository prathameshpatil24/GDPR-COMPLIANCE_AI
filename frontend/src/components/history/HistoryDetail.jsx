import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'

import ComplianceReport from '@/components/results/ComplianceReport'
import ViolationReport from '@/components/results/ViolationReport'
import { Button } from '@/components/ui/button'

/**
 * Full report for an expanded history row.
 * @param {{
 *   detail: object | null,
 *   loading: boolean,
 *   error: string | null,
 *   onCollapse: () => void,
 * }} props
 */
export default function HistoryDetail({ detail, loading, error, onCollapse }) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: reduceMotion ? 0 : 0.25 }}
      className="overflow-hidden border-t border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-950/30"
    >
      <div className="p-4">
        <div className="mb-4 flex justify-end">
          <Button type="button" variant="ghost" size="sm" onClick={onCollapse}>
            Collapse
          </Button>
        </div>
        {loading ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading analysis…</p>
        ) : error ? (
          <p className="text-sm text-rose-600 dark:text-rose-400" role="alert">
            {error}
          </p>
        ) : detail?.mode === 'violation_analysis' && detail.result ? (
          <ViolationReport
            analysisId={detail.analysis_id}
            result={detail.result}
            completedAt={detail.created_at}
          />
        ) : detail?.mode === 'compliance_assessment' && detail.result ? (
          <ComplianceReport
            analysisId={detail.analysis_id}
            result={detail.result}
            completedAt={detail.created_at}
          />
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">No report data.</p>
        )}
      </div>
    </motion.div>
  )
}
