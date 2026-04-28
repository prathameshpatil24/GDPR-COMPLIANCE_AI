import { Activity, Clock, Coins, Wallet } from 'lucide-react'
import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { Link, useNavigate } from 'react-router-dom'

import CostChart from '@/components/stats/CostChart'
import LatencyChart from '@/components/stats/LatencyChart'
import ModeChart from '@/components/stats/ModeChart'
import QueryChart from '@/components/stats/QueryChart'
import SeverityChart from '@/components/stats/SeverityChart'
import StatCard from '@/components/stats/StatCard'
import EmptyState from '@/components/shared/EmptyState'
import Skeleton from '@/components/shared/Skeleton'
import { Button } from '@/components/ui/button'
import { useStats } from '@/hooks/useStats'

/**
 * Usage dashboard backed by `/api/v1/stats`.
 */
export default function StatsPage() {
  const { stats, loading, error, refetch } = useStats()
  const navigate = useNavigate()
  const reduceMotion = useReducedMotion()

  const onSeverityClick = (key) => {
    if (key === 'unknown') return
    navigate(`/history?severity=${encodeURIComponent(key)}`)
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Dashboard</h1>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Skeleton className="h-64 w-full lg:col-span-2" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl space-y-4">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Dashboard</h1>
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-700 dark:text-rose-400"
        >
          <span>{error}</span>
          <Button type="button" size="sm" variant="secondary" onClick={() => void refetch()}>
            Retry
          </Button>
        </div>
      </div>
    )
  }

  const total = stats?.total_queries ?? 0
  if (!total) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Dashboard</h1>
        <EmptyState
          title="No data yet"
          description="Run your first analysis to see dashboard metrics."
          action={
            <Link
              to="/"
              className="mt-4 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
            >
              Go to Analyze →
            </Link>
          }
        />
      </div>
    )
  }

  const cardMotion = {
    initial: reduceMotion ? false : { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: reduceMotion ? 0 : 0.35 },
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Aggregates from the query log (same source as <span className="font-mono">gdpr-check stats</span>).
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <motion.div {...cardMotion} transition={{ ...cardMotion.transition, delay: reduceMotion ? 0 : 0 }}>
          <StatCard
            label="Total queries"
            subtitle="Analyses run"
            icon={Activity}
            value={stats.total_queries}
            format={(n) => String(Math.round(n))}
          />
        </motion.div>
        <motion.div
          {...cardMotion}
          transition={{ ...cardMotion.transition, delay: reduceMotion ? 0 : 0.05 }}
        >
          <StatCard
            label="Avg latency"
            subtitle="Per analysis"
            icon={Clock}
            value={stats.avg_latency_ms / 1000}
            format={(n) => `${n.toFixed(1)}s`}
          />
        </motion.div>
        <motion.div
          {...cardMotion}
          transition={{ ...cardMotion.transition, delay: reduceMotion ? 0 : 0.1 }}
        >
          <StatCard
            label="Avg cost"
            subtitle="Per analysis"
            icon={Coins}
            value={stats.avg_cost_eur}
            format={(n) =>
              new Intl.NumberFormat(undefined, {
                style: 'currency',
                currency: 'EUR',
                maximumFractionDigits: 4,
              }).format(n)
            }
          />
        </motion.div>
        <motion.div
          {...cardMotion}
          transition={{ ...cardMotion.transition, delay: reduceMotion ? 0 : 0.15 }}
        >
          <StatCard
            label="Total cost"
            subtitle="Total spend"
            icon={Wallet}
            value={stats.total_cost_eur}
            format={(n) =>
              new Intl.NumberFormat(undefined, {
                style: 'currency',
                currency: 'EUR',
                maximumFractionDigits: 4,
              }).format(n)
            }
          />
        </motion.div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.35, delay: reduceMotion ? 0 : 0.2 }}
        >
          <CostChart data={stats.cost_by_day} />
        </motion.div>
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.35, delay: reduceMotion ? 0 : 0.3 }}
        >
          <LatencyChart data={stats.latency_by_day} />
        </motion.div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <motion.div
          className="lg:col-span-2"
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.35, delay: reduceMotion ? 0 : 0.4 }}
        >
          <QueryChart data={stats.queries_by_day} />
        </motion.div>
        <div className="flex flex-col gap-4">
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.35, delay: reduceMotion ? 0 : 0.5 }}
          >
            <SeverityChart distribution={stats.severity_distribution} onSegmentClick={onSeverityClick} />
          </motion.div>
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.35, delay: reduceMotion ? 0 : 0.6 }}
          >
            <ModeChart distribution={stats.mode_distribution} />
          </motion.div>
        </div>
      </div>
    </div>
  )
}
