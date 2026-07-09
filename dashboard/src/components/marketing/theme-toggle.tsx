'use client'

import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'

/**
 * Standalone theme toggle for public (marketing/auth) pages, where the config
 * store isn't hydrated. Persists to the same localStorage keys the no-flash
 * script and dashboard store read, so the choice carries across the app.
 */
export function PublicThemeToggle({ className }: { className?: string }) {
  const [dark, setDark] = useState(false)

  useEffect(() => {
    // Read the theme applied by the no-flash script once on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDark(document.documentElement.classList.contains('dark'))
  }, [])

  function toggle() {
    const next = !dark
    setDark(next)
    document.documentElement.classList.toggle('dark', next)
    try {
      localStorage.setItem('aegis-theme', next ? 'dark' : 'light')
    } catch {
      /* ignore */
    }
  }

  return (
    <button
      onClick={toggle}
      aria-label="Toggle theme"
      className={`focus-ring inline-flex size-9 items-center justify-center rounded-lg border border-border text-muted transition-colors hover:bg-surface-2 ${className ?? ''}`}
    >
      {dark ? <Sun className="size-4.5" /> : <Moon className="size-4.5" />}
    </button>
  )
}
