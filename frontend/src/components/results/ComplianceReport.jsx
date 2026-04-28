import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'

import ConfidenceChart from '@/components/results/ConfidenceChart'
import DataFlowDiagram from '@/components/results/DataFlowDiagram'
import FindingCard from '@/components/results/FindingCard'
import RecommendationList from '@/components/results/RecommendationList'
import RiskOverviewChart from '@/components/results/RiskOverviewChart'
import SeverityBadge from '@/components/results/SeverityBadge'
import { cn } from '@/lib/utils'

const FINDING_ORDER = { non_compliant: 0, at_risk: 1, insufficient_info: 2, compliant: 3 }

/**
 * Normalize finding status for sorting and badges.
 * @param {string} raw
 * @returns {string}
 */
function normalizeLevel(raw) {
  if (raw == null) return 'unknown'
  const s = String(raw).toLowerCase().trim().replace(/\s+/g, '_').replace(/-/g, '_')
  if (s === 'noncompliant') return 'non_compliant'
  return s
}

/**
 * Map overall risk string to severity badge keys (low | medium | high | critical | unknown).
 * @param {string} raw
 * @returns {string}
 */
function riskToSeverity(raw) {
  const k = String(raw || '')
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '_')
    .replace(/-/g, '_')
  if (k === 'low' || k === 'medium' || k === 'high' || k === 'critical' || k === 'unknown') return k
  return 'unknown'
}

/**
 * @param {string} level
 */
function executiveBorderClass(level) {
  const k = riskToSeverity(level)
  if (k === 'low') return 'border-l-emerald-500'
  if (k === 'critical') return 'border-l-rose-500'
  if (k === 'high' || k === 'medium') return 'border-l-amber-500'
  return 'border-l-slate-500'
}

/**
 * Deduped remediation strings from findings.
 * @param {Array<{ remediation?: string | null }>} findings
 * @returns {string[]}
 */
function remediationRecommendations(findings) {
  const seen = new Set()
  const out = []
  for (const f of findings || []) {
    const r = f.remediation?.trim()
    if (r && !seen.has(r)) {
      seen.add(r)
      out.push(r)
    }
  }
  return out
}

/**
 * @param {Array<{ status?: string }>} findings
 */
function sortFindings(findings) {
  return [...(findings || [])].sort((a, b) => {
    const ra = FINDING_ORDER[normalizeLevel(a.status)] ?? 99
    const rb = FINDING_ORDER[normalizeLevel(b.status)] ?? 99
    return ra - rb
  })
}

/**
 * Full compliance assessment report from API `result` object.
 * @param {{ analysisId: string, result: object, completedAt?: string | null }} props
 */
export default function ComplianceReport({ analysisId, result, completedAt }) {
  const reduceMotion = useReducedMotion()
  const riskSeverity = riskToSeverity(result.overall_risk_level)
  const findings = sortFindings(result.findings)
  const recs = remediationRecommendations(findings)
  const flows = result.data_map?.data_flows
  const ts =
    completedAt != null && completedAt !== ''
      ? new Date(completedAt).toLocaleString()
      : null

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
            {result.system_name || 'System assessment'}
          </h1>
          <SeverityBadge level={riskSeverity} />
          <p className="font-mono text-xs text-slate-500 dark:text-slate-500">{analysisId}</p>
          {ts ? <p className="text-sm text-slate-600 dark:text-slate-400">{ts}</p> : null}
        </div>
      </header>

      <motion.section
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className={cn(
          'rounded-xl border border-slate-200 border-l-4 bg-slate-100/80 p-6 dark:border-slate-800 dark:bg-slate-800/50',
          executiveBorderClass(result.overall_risk_level)
        )}
      >
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500">
          Executive summary
        </h2>
        <p className="text-sm leading-relaxed text-slate-800 dark:text-slate-200">{result.summary}</p>
      </motion.section>

      <RiskOverviewChart findings={findings} />

      <section>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Compliance findings</h2>
          <span className="rounded-full bg-slate-200 px-2 py-0.5 font-mono text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
            {findings.length}
          </span>
        </div>
        <div className="space-y-3">
          {findings.map((f, i) => (
            <FindingCard key={`${f.area}-${i}`} finding={f} index={i} />
          ))}
        </div>
      </section>

      <ConfidenceChart findings={findings} />

      {result.data_map && Array.isArray(flows) && flows.length > 0 ? (
        <DataFlowDiagram flows={flows} />
      ) : null}

      {recs.length ? (
        <section>
          <h2 className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-50">
            Recommendations
          </h2>
          <RecommendationList items={recs} />
        </section>
      ) : null}

      <p className="text-xs italic text-slate-500 dark:text-slate-600">
        Informational only; not legal advice.
      </p>
    </div>
  )
}
