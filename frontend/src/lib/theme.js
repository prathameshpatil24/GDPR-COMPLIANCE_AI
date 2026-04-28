/** Violation severity display config (dark-first tokens). */
export const severityConfig = {
  low: { label: 'Low', color: 'text-emerald-400', bg: 'bg-emerald-500/10', pulse: false },
  medium: { label: 'Medium', color: 'text-amber-500', bg: 'bg-amber-500/10', pulse: false },
  high: { label: 'High', color: 'text-orange-500', bg: 'bg-orange-500/10', pulse: false },
  critical: { label: 'Critical', color: 'text-rose-500', bg: 'bg-rose-500/15', pulse: true },
  unknown: { label: 'Unknown', color: 'text-slate-500', bg: 'bg-slate-500/10', pulse: false },
}

/** Compliance finding status display config. */
export const statusConfig = {
  compliant: { label: 'Compliant', color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  at_risk: { label: 'At Risk', color: 'text-amber-500', bg: 'bg-amber-500/10' },
  non_compliant: { label: 'Non-Compliant', color: 'text-rose-500', bg: 'bg-rose-500/10' },
  insufficient_info: { label: 'Insufficient Info', color: 'text-slate-500', bg: 'bg-slate-500/10' },
}
