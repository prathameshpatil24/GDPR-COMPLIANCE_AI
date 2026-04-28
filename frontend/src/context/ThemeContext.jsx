/* eslint-disable react-refresh/only-export-components -- paired Provider + useTheme hook */
import { createContext, useContext, useEffect, useState } from 'react'

const STORAGE_KEY = 'gdpr-ai-theme'

const ThemeContext = createContext(
  /** @type {{ isDark: boolean, setIsDark: (v: boolean) => void, toggleTheme: () => void }} */ ({
    isDark: true,
    setIsDark: () => {},
    toggleTheme: () => {},
  })
)

/**
 * Theme provider: dark is default; persists to localStorage and `html.dark`.
 * @param {{ children: import('react').ReactNode }} props
 */
export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(() => {
    if (typeof window === 'undefined') return true
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light') return false
    return true
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
    localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light')
  }, [isDark])

  const toggleTheme = () => setIsDark((d) => !d)

  return (
    <ThemeContext.Provider value={{ isDark, setIsDark, toggleTheme }}>{children}</ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}
