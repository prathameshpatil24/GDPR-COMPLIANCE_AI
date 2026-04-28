import { X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

/**
 * Shown when health check fails; dismissable, auto re-shows on interval.
 * @param {{ visible: boolean, onDismiss: () => void }} props
 */
export default function BackendOfflineBanner({ visible, onDismiss }) {
  if (!visible) return null

  return (
    <div
      role="alert"
      className={cn(
        'flex items-center justify-between gap-3 border-b border-rose-500/20 bg-rose-500/10 px-4 py-2 text-sm text-rose-700',
        'dark:text-rose-400'
      )}
    >
      <p>
        Backend is unreachable. Make sure <span className="font-mono">gdpr-check serve</span> is running.
      </p>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-8 w-8 shrink-0 text-rose-600 hover:bg-rose-500/10 dark:text-rose-400"
        onClick={onDismiss}
        aria-label="Dismiss backend warning"
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  )
}
