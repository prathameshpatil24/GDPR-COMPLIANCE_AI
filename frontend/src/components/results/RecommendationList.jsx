import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'

/**
 * Numbered recommendations with left accent and stagger.
 * @param {{ items: string[] }} props
 */
export default function RecommendationList({ items }) {
  const reduceMotion = useReducedMotion()
  if (!items?.length) return null

  return (
    <ol className="space-y-3">
      {items.map((text, i) => (
        <motion.li
          key={`${i}-${text.slice(0, 24)}`}
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: reduceMotion ? 0 : i * 0.06, duration: 0.35 }}
          className="border-l-2 border-indigo-500/50 bg-slate-100/80 py-3 pl-4 text-sm leading-relaxed text-slate-700 dark:bg-slate-800/30 dark:text-slate-300"
        >
          <span className="font-mono text-xs text-slate-500 dark:text-slate-500">{i + 1}.</span>{' '}
          {text}
        </motion.li>
      ))}
    </ol>
  )
}
