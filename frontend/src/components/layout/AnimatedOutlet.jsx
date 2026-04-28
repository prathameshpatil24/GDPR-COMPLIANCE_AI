import { AnimatePresence } from 'framer-motion'
import { Outlet, useLocation } from 'react-router-dom'

import PageTransition from '@/components/layout/PageTransition'

/**
 * Outlet with exit/enter transitions between routes.
 */
export default function AnimatedOutlet() {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <PageTransition key={location.pathname}>
        <Outlet />
      </PageTransition>
    </AnimatePresence>
  )
}
