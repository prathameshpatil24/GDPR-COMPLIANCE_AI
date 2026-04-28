import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { healthCheck } from '@/api/client'
import AnimatedOutlet from '@/components/layout/AnimatedOutlet'
import BackendOfflineBanner from '@/components/layout/BackendOfflineBanner'
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import ErrorBoundary from '@/components/shared/ErrorBoundary'
import Skeleton from '@/components/shared/Skeleton'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AnalysisCountProvider } from '@/context/AnalysisCountContext'
import { AnalyzeProvider } from '@/context/AnalyzeContext'
import { DebugProvider } from '@/context/DebugContext'
import { ShellLayoutProvider, useShellLayout } from '@/context/ShellLayoutContext'
import { ThemeProvider } from '@/context/ThemeContext'
import { ToastProvider } from '@/context/ToastContext'
import { cn } from '@/lib/utils'

const AnalyzePage = lazy(() => import('@/pages/AnalyzePage'))
const HistoryPage = lazy(() => import('@/pages/HistoryPage'))
const StatsPage = lazy(() => import('@/pages/StatsPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))

function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center p-8">
      <div className="w-full max-w-md space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-10 w-3/4" />
      </div>
    </div>
  )
}

function AppShell() {
  const [health, setHealth] = useState(null)
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const { isLg, desktopCollapsed, mobileOpen } = useShellLayout()

  const refreshHealth = useCallback(() => {
    healthCheck()
      .then((res) => {
        setHealth({ ok: true, version: res.data.version, status: res.data.status })
      })
      .catch(() => {
        setHealth({ ok: false })
      })
  }, [])

  useEffect(() => {
    refreshHealth()
  }, [refreshHealth])

  useEffect(() => {
    const id = window.setInterval(() => {
      setBannerDismissed(false)
      refreshHealth()
    }, 30000)
    return () => window.clearInterval(id)
  }, [refreshHealth])

  const mainOffset = cn(
    'flex min-h-screen flex-col transition-[margin] duration-300',
    isLg && desktopCollapsed && 'lg:ml-16',
    isLg && !desktopCollapsed && 'lg:ml-64',
    !isLg && mobileOpen && 'ml-64',
    !isLg && !mobileOpen && 'ml-16'
  )

  const showBackendBanner = health?.ok === false && !bannerDismissed

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-50">
      <Sidebar />
      <div className={mainOffset}>
        <BackendOfflineBanner
          visible={showBackendBanner}
          onDismiss={() => setBannerDismissed(true)}
        />
        <Header health={health} />
        <main className="flex-1 px-4 py-6 sm:px-6 sm:py-8">
          <ErrorBoundary>
            <Suspense fallback={<RouteFallback />}>
              <Routes>
                <Route element={<AnimatedOutlet />}>
                  <Route path="/" element={<AnalyzePage />} />
                  <Route path="/history" element={<HistoryPage />} />
                  <Route path="/stats" element={<StatsPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Route>
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <BrowserRouter>
          <TooltipProvider>
            <DebugProvider>
              <AnalysisCountProvider>
                <AnalyzeProvider>
                  <ShellLayoutProvider>
                    <AppShell />
                  </ShellLayoutProvider>
                </AnalyzeProvider>
              </AnalysisCountProvider>
            </DebugProvider>
          </TooltipProvider>
        </BrowserRouter>
      </ToastProvider>
    </ThemeProvider>
  )
}
