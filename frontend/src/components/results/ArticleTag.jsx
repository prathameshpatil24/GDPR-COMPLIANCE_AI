import { ExternalLink } from 'lucide-react'

import { getArticleUrl } from '@/lib/articleLinks'
import { cn } from '@/lib/utils'

const basePill =
  'inline-flex items-center gap-0.5 rounded-md bg-indigo-500/10 px-2 py-0.5 font-mono text-xs text-indigo-600 transition-colors dark:text-indigo-400'

/**
 * Monospace pill for legal article references; links to gdpr-info / BDSG when URL is known.
 * @param {{ label: string, className?: string }} props
 */
export default function ArticleTag({ label, className }) {
  const url = getArticleUrl(label)

  if (url) {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          basePill,
          'group cursor-pointer hover:bg-indigo-500/20 hover:text-indigo-700 hover:underline hover:underline-offset-2 dark:hover:text-indigo-300',
          className
        )}
      >
        {label}
        <ExternalLink
          className="h-3 w-3 shrink-0 opacity-40 transition-opacity group-hover:opacity-100"
          aria-hidden
        />
      </a>
    )
  }

  return (
    <span className={cn(basePill, className)}>{label}</span>
  )
}
