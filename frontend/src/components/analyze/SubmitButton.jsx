import { Loader2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { useReducedMotion } from '@/hooks/useReducedMotion'
import { cn } from '@/lib/utils'

/**
 * Primary analyze action with tap feedback and optional ripple.
 * @param {{ onClick: () => void, loading: boolean, disabled?: boolean, label?: string }} props
 */
export default function SubmitButton({ onClick, loading, disabled = false, label = 'Analyze' }) {
  const reduceMotion = useReducedMotion()
  const [ripples, setRipples] = useState([])

  const handlePointerDown = (e) => {
    if (reduceMotion || loading || disabled) return
    const el = e.currentTarget
    const rect = el.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const id = Date.now() + Math.random()
    setRipples((r) => [...r, { id, x, y }])
    window.setTimeout(() => setRipples((r) => r.filter((i) => i.id !== id)), 650)
  }

  return (
    <motion.div
      className="relative inline-block overflow-hidden rounded-lg"
      whileTap={reduceMotion || loading || disabled ? undefined : { scale: 1.02 }}
      transition={{ duration: 0.15 }}
    >
      {!reduceMotion ? (
        <span className="pointer-events-none absolute inset-0 overflow-hidden rounded-lg" aria-hidden>
          {ripples.map((r) => (
            <span
              key={r.id}
              className="gdpr-ripple-dot absolute rounded-full bg-indigo-400/30"
              style={{ left: r.x, top: r.y }}
            />
          ))}
        </span>
      ) : null}
      <Button
        type="button"
        size="lg"
        disabled={disabled || loading}
        className={cn('relative z-10 min-w-[8rem]')}
        onPointerDown={handlePointerDown}
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
