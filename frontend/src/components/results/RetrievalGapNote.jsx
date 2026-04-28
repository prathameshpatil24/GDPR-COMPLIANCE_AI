import * as Collapsible from '@radix-ui/react-collapsible'
import { ChevronDown } from 'lucide-react'
import { useState } from 'react'

import { cn } from '@/lib/utils'

/**
 * Ungrounded / retrieval gap callout.
 * @param {{ notes: string[] }} props
 */
export default function RetrievalGapNote({ notes }) {
  const [open, setOpen] = useState(true)
  if (!notes?.length) return null

  return (
    <section className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 dark:bg-amber-500/5">
      <Collapsible.Root open={open} onOpenChange={setOpen}>
        <Collapsible.Trigger className="flex w-full items-center justify-between gap-2 text-left">
          <h3 className="text-sm font-semibold text-amber-700 dark:text-amber-400">
            Not Grounded (Retrieval Gaps)
          </h3>
          <ChevronDown
            className={cn('h-4 w-4 shrink-0 text-amber-600 transition-transform', open && 'rotate-180')}
            aria-hidden
          />
        </Collapsible.Trigger>
        <Collapsible.Content className="mt-3 overflow-hidden">
          <ul className="list-inside list-disc space-y-2 text-sm text-amber-800 dark:text-amber-400">
            {notes.map((n, i) => (
              <li key={`${i}-${n.slice(0, 32)}`}>{n}</li>
            ))}
          </ul>
        </Collapsible.Content>
      </Collapsible.Root>
    </section>
  )
}
