/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useState } from 'react'

import { useMediaQuery } from '@/hooks/useMediaQuery'

const ShellLayoutContext = createContext(null)

const STORAGE_KEY = 'gdpr-ai-sidebar-collapsed'

/**
 * Responsive sidebar: desktop collapse + mobile expand from icon rail.
 * @param {{ children: import('react').ReactNode }} props
 */
export function ShellLayoutProvider({ children }) {
  const isLg = useMediaQuery('(min-width: 1024px)')
  const [desktopCollapsed, setDesktopCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem(STORAGE_KEY) === 'true'
  })
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, String(desktopCollapsed))
  }, [desktopCollapsed])

  const toggleDesktopCollapsed = useCallback(() => setDesktopCollapsed((c) => !c), [])
  const toggleMobile = useCallback(() => setMobileOpen((o) => !o), [])
  const closeMobile = useCallback(() => setMobileOpen(false), [])

  /** Wide sidebar: desktop expanded, or mobile sheet open */
  const sidebarWide = isLg ? !desktopCollapsed : mobileOpen

  const value = {
    isLg,
    desktopCollapsed,
    toggleDesktopCollapsed,
    mobileOpen,
    toggleMobile,
    closeMobile,
    sidebarWide,
  }

  return <ShellLayoutContext.Provider value={value}>{children}</ShellLayoutContext.Provider>
}

export function useShellLayout() {
  const ctx = useContext(ShellLayoutContext)
  if (!ctx) throw new Error('useShellLayout must be used within ShellLayoutProvider')
  return ctx
}
