import { motion } from 'framer-motion'

import { useReducedMotion } from '@/hooks/useReducedMotion'

const ease = [0.25, 0.1, 0.25, 1]

/**
 * Framer Motion wrapper for route segments (use with AnimatePresence + key).
 * @param {{ children: import('react').ReactNode }} props
 */
export default function PageTransition({ children }) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      initial={reduceMotion ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduceMotion ? { opacity: 1, y: 0 } : { opacity: 0, y: -10 }}
      transition={{
        duration: reduceMotion ? 0 : 0.4,
        ease,
      }}
    >
      {children}
    </motion.div>
  )
}
