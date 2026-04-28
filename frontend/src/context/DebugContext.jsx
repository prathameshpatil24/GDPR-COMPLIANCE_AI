/* eslint-disable react-refresh/only-export-components -- Provider + hooks */
import { createContext, useCallback, useContext, useMemo, useState } from 'react'

const DEBUG_CODE = '009594'

const DebugContext = createContext(
  /** @type {{ debugMode: boolean, unlock: (code: string) => boolean, lock: () => void }} */ ({
    debugMode: false,
    unlock: () => false,
    lock: () => {},
  })
)

/**
 * Optional developer visibility (e.g. chunk IDs). Resets on full page reload — not persisted.
 * @param {{ children: import('react').ReactNode }} props
 */
export function DebugProvider({ children }) {
  const [debugMode, setDebugMode] = useState(false)

  const unlock = useCallback((code) => {
    if (code === DEBUG_CODE) {
      setDebugMode(true)
      return true
    }
    return false
  }, [])

  const lock = useCallback(() => setDebugMode(false), [])

  const value = useMemo(
    () => ({
      debugMode,
      unlock,
      lock,
    }),
    [debugMode, unlock, lock]
  )

  return <DebugContext.Provider value={value}>{children}</DebugContext.Provider>
}

export function useDebug() {
  return useContext(DebugContext)
}
