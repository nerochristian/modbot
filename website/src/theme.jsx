import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const ThemeContext = createContext(null)

export function ThemeProvider({ children }) {
  useEffect(() => {
    document.documentElement.dataset.theme = 'dark'
  }, [])

  const value = useMemo(() => ({
    theme: 'dark',
    isLight: false,
    toggleTheme: () => {},
  }), [])

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used within ThemeProvider')
  return context
}

export function ThemeToggle({ className = '' }) {
  return null
}
