import { useTheme } from '@/context/ThemeContext'

/**
 * Recharts / chart styling tokens for current theme.
 * @returns {object}
 */
export function useChartColors() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return {
    grid: isDark ? '#1e293b' : '#e2e8f0',
    axis: isDark ? '#94a3b8' : '#64748b',
    tooltipBg: isDark ? '#1e293b' : '#ffffff',
    tooltipBorder: isDark ? '#334155' : '#e2e8f0',
    tooltipText: isDark ? '#f8fafc' : '#0f172a',
    tooltipMuted: isDark ? '#94a3b8' : '#64748b',
    primary: '#6366f1',
    primaryArea: isDark ? 'rgba(99,102,241,0.1)' : 'rgba(99,102,241,0.08)',
    amber: '#f59e0b',
    amberArea: isDark ? 'rgba(245,158,11,0.1)' : 'rgba(245,158,11,0.08)',
  }
}
