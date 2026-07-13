'use client'

import { useEffect, useRef } from 'react'
import { useConfigStore, type SessionUser } from '@/lib/store'
import type { DashboardConfig } from '@/lib/dashboard-config'
import { useToast } from '@/components/ui/toast'

/**
 * Hydrates the config store from server-provided data and persists subsequent
 * changes to the backend (debounced). Also keeps the DOM theme in sync when the
 * OS color scheme changes while the app is on "system".
 */
export function ConfigProvider({
  config,
  user,
  children,
}: {
  config: DashboardConfig
  user: SessionUser
  children: React.ReactNode
}) {
  const toast = useToast()
  const toastRef = useRef(toast)
  const hydrate = useConfigStore((s) => s.hydrate)
  const savedAt = useConfigStore((s) => s.savedAt)
  const configState = useConfigStore((s) => s.config)
  const firstSave = useRef(true)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    toastRef.current = toast
  }, [toast])

  // Hydrate once on mount.
  useEffect(() => {
    hydrate(config, user)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // React to OS theme changes while on "system".
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => {
      const c = useConfigStore.getState().config
      if (c.theme === 'system') {
        document.documentElement.classList.toggle('dark', mq.matches)
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  // Debounced persistence whenever the config changes (skips the initial hydrate).
  useEffect(() => {
    if (savedAt === 0) return
    if (firstSave.current) {
      firstSave.current = false
    }
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      const response = await fetch('/api/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configState),
      }).catch(() => null)
      if (!response?.ok) {
        toastRef.current.error('Preferences were not saved', 'Check your connection and try the change again.')
      }
    }, 600)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [savedAt, configState])

  return <>{children}</>
}
