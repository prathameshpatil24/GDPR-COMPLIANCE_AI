/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState } from 'react'

const STORAGE_KEY = 'gdpr-ai-theme'

const ThemeContext = createContext(
  /** @type {{ theme: string, setTheme: (t: string) => void, toggleTheme: () => void, isDark: boolean, setIsDark: (v: boolean) => void }} */ ({
    theme: 'dark',
    setTheme: () => {},
    toggleTheme: () => {},
    isDark: true,
    setIsDark: () => {},
  })
)

/**
 * Persists light/dark on `html.dark` and localStorage.
 * @param {{ children: import('react').ReactNode }} props
 */
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark'
    return localStorage.getItem(STORAGE_KEY) || 'dark'
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  const setIsDark = (v) => setTheme(v ? 'dark' : 'light')
  const isDark = theme === 'dark'

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, isDark, setIsDark }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}
