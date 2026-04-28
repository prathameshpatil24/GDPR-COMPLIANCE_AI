import { useEffect, useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { healthCheck } from '@/api/client'
import AnimatedOutlet from '@/components/layout/AnimatedOutlet'
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import { NavMetricsProvider } from '@/context/NavMetricsContext'
import { ThemeProvider } from '@/context/ThemeContext'
import { ToastProvider } from '@/context/ToastContext'
import AnalyzePage from '@/pages/AnalyzePage'
import HistoryPage from '@/pages/HistoryPage'
import SettingsPage from '@/pages/SettingsPage'
import StatsPage from '@/pages/StatsPage'

function AppShell() {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    let cancelled = false
    healthCheck()
      .then((res) => {
        if (!cancelled) setHealth({ ok: true, version: res.data.version, status: res.data.status })
      })
      .catch(() => {
        if (!cancelled) setHealth({ ok: false })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-50">
      <Sidebar />
      <div className="ml-64 flex min-h-screen flex-col">
        <Header health={health} />
        <main className="flex-1 px-6 py-8">
          <Routes>
            <Route element={<AnimatedOutlet />}>
              <Route path="/" element={<AnalyzePage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/stats" element={<StatsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Routes>
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
          <NavMetricsProvider>
            <AppShell />
          </NavMetricsProvider>
        </BrowserRouter>
      </ToastProvider>
    </ThemeProvider>
  )
}
