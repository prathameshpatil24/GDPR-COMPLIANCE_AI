import StatCard from '@/components/stats/StatCard'

/**
 * Usage dashboard (Milestone 4: wire to /api/v1/stats when available).
 */
export default function StatsPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Aggregates will connect to a future <span className="font-mono">/api/v1/stats</span> endpoint;
        CLI stats exist today via <span className="font-mono">gdpr-check stats</span>.
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard label="Total queries" value="0" />
        <StatCard label="Avg latency" value="—" hint="ms" />
        <StatCard label="Avg cost" value="€0.0000" />
        <StatCard label="Total cost" value="€0.0000" />
        <StatCard label="Total tokens" value="0" />
        <StatCard label="Avg violations / query" value="0" />
      </div>
    </div>
  )
}
