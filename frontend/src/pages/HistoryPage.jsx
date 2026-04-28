import { Inbox } from 'lucide-react'

import EmptyState from '@/components/shared/EmptyState'

/**
 * Past analyses list (Milestone 4).
 */
export default function HistoryPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <EmptyState
        icon={<Inbox className="h-10 w-10" aria-hidden />}
        title="No analyses yet"
        description="Run your first analysis from the Analyze page to see results here. A list API will be added when the backend exposes history endpoints."
      />
    </div>
  )
}
