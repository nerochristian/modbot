import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { Moon, Sun } from 'lucide-react'

const ThemeContext = createContext(null)
const STORAGE_KEY = 'orion-theme'

function getInitialTheme() {
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return stored === 'light' || stored === 'dark' ? stored : 'dark'
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(getInitialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  const value = useMemo(() => ({
    theme,
    isLight: theme === 'light',
    toggleTheme: () => setTheme(current => current === 'light' ? 'dark' : 'light'),
  }), [theme])

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}

export function ThemeToggle({ className = '' }) {
  const { isLight, toggleTheme } = useTheme()
  const Icon = isLight ? Moon : Sun
  const label = isLight ? 'Switch to dark mode' : 'Switch to light mode'

  return (
    <button
      type="button"
      className={`theme-toggle ${className}`.trim()}
      onClick={toggleTheme}
      aria-label={label}
      title={label}
    >
      <Icon size={16} />
      <span>{isLight ? 'Dark' : 'Light'}</span>
    </button>
  )
}
