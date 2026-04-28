import * as Collapsible from '@radix-ui/react-collapsible'
import { ChevronDown } from 'lucide-react'
import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'
import { useEffect, useState } from 'react'

import ArticleTag from '@/components/results/ArticleTag'
import StatusBadge from '@/components/results/StatusBadge'
import { cn } from '@/lib/utils'

/**
 * Expandable compliance finding.
 * @param {{ finding: object, index: number }} props
 */
export default function FindingCard({ finding, index }) {
  const [open, setOpen] = useState(false)
  const reduceMotion = useReducedMotion()
  const articles = finding.relevant_articles || []
  const visible = articles.slice(0, 3)
  const more = articles.length - visible.length

  useEffect(() => {
    if (!open) return
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: reduceMotion ? 0 : index * 0.06, duration: 0.35 }}
    >
      <Collapsible.Root open={open} onOpenChange={setOpen}>
        <div className="rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
          <Collapsible.Trigger
            className="flex w-full cursor-pointer items-center gap-3 rounded-xl p-4 text-left transition-colors hover:bg-slate-100/80 dark:hover:bg-slate-800/40"
            type="button"
          >
            <div className="min-w-0 flex-1">
              <p className="font-medium text-slate-900 dark:text-slate-50">{finding.area}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {visible.map((a) => (
                  <ArticleTag key={a} label={a} />
                ))}
                {more > 0 ? (
                  <span className="text-xs text-slate-500 dark:text-slate-500">+{more} more</span>
                ) : null}
              </div>
            </div>
            <StatusBadge status={finding.status} />
            <ChevronDown
              className={cn('h-5 w-5 shrink-0 text-slate-500 transition-transform', open && 'rotate-180')}
              aria-hidden
            />
          </Collapsible.Trigger>
          <Collapsible.Content className="overflow-hidden border-t border-slate-200 dark:border-slate-800">
            <div className="space-y-4 px-4 pb-4 pt-3">
              <div>
                <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500">
                  Description
                </h4>
                <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                  {finding.description}
                </p>
              </div>
              <div>
                <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500">
                  Relevant articles
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {articles.map((a) => (
                    <ArticleTag key={a} label={a} />
                  ))}
                </div>
              </div>
              {finding.remediation ? (
                <div className="border-l-2 border-indigo-500/30 pl-4">
                  <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500">
                    Remediation
                  </h4>
                  <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                    {finding.remediation}
                  </p>
                </div>
              ) : null}
              {finding.technical_guidance ? (
                <div className="border-l-2 border-emerald-500/30 pl-4">
                  <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-500">
                    Technical guidance
                  </h4>
                  <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                    {finding.technical_guidance}
                  </p>
                </div>
              ) : null}
            </div>
          </Collapsible.Content>
        </div>
      </Collapsible.Root>
    </motion.div>
  )
}
