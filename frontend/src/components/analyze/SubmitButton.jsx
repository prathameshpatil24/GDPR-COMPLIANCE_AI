import { Loader2 } from 'lucide-react'
import { motion, useReducedMotion } from 'framer-motion'

import { Button } from '@/components/ui/button'

/**
 * Primary analyze action with loading and tap feedback.
 * @param {{ onClick: () => void, loading: boolean, disabled?: boolean, label?: string }} props
 */
export default function SubmitButton({ onClick, loading, disabled = false, label = 'Analyze' }) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div whileTap={reduceMotion || loading || disabled ? undefined : { scale: 0.97 }}>
      <Button
        type="button"
        size="lg"
        disabled={disabled || loading}
        className="min-w-[8rem]"
        onClick={onClick}
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Analyzing…
          </>
        ) : (
          label
        )}
      </Button>
    </motion.div>
  )
}
