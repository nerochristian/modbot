'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

type State<T> = { data: T | null; error: string | null; loading: boolean }

/**
 * Client fetch hook with loading/error state, manual refetch, and optional
 * auto-refresh. Used across dashboard pages so every data view has consistent
 * loading, error, and empty handling.
 */
export function useApi<T>(url: string, options?: { refreshInterval?: number; enabled?: boolean }) {
  const enabled = options?.enabled ?? true
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: enabled })
  const abortRef = useRef<AbortController | null>(null)

  const fetchData = useCallback(
    async (silent = false) => {
      if (!enabled) return
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      if (!silent) setState((s) => ({ ...s, loading: true, error: null }))
      try {
        const res = await fetch(url, { signal: controller.signal })
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.error || `Request failed (${res.status})`)
        }
        const data = (await res.json()) as T
        setState({ data, error: null, loading: false })
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        setState((s) => ({ data: s.data, error: (err as Error).message, loading: false }))
      }
    },
    [url, enabled],
  )

  useEffect(() => {
    fetchData()
    return () => abortRef.current?.abort()
  }, [fetchData])

  // Auto-refresh on interval (seconds); 0/undefined disables.
  const interval = options?.refreshInterval ?? 0
  useEffect(() => {
    if (!interval || !enabled) return
    const id = setInterval(() => fetchData(true), interval * 1000)
    return () => clearInterval(id)
  }, [interval, enabled, fetchData])

  return { ...state, refetch: () => fetchData() }
}
