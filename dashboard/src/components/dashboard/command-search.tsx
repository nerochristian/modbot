'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createPortal } from 'react-dom'
import { Search, CornerDownLeft } from 'lucide-react'
import { NAV_ITEMS } from '@/lib/nav'
import { useConfigStore } from '@/lib/store'
import { cn } from '@/lib/utils'

export function CommandSearch() {
  const router = useRouter()
  const permissions = useConfigStore((s) => s.user?.permissions ?? [])
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const items = useMemo(
    () => NAV_ITEMS.filter((i) => permissions.includes(i.permission)),
    [permissions],
  )
  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return items
    return items.filter((i) => i.label.toLowerCase().includes(q))
  }, [items, query])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (open) {
      // Reset the palette's query/selection each time it opens.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setQuery('')
      setActive(0)
      setTimeout(() => inputRef.current?.focus(), 0)
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
  }, [open])

  function go(href: string) {
    setOpen(false)
    router.push(href)
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="focus-ring flex h-9 w-full items-center gap-2 rounded-lg border border-border bg-surface-2/60 px-3 text-sm text-muted-2 transition-colors hover:bg-surface-2 sm:w-64"
      >
        <Search className="size-4" />
        <span className="flex-1 text-left">Jump to…</span>
        <kbd className="hidden rounded border border-border bg-surface px-1.5 py-0.5 font-mono text-[10px] text-muted-2 sm:inline">
          ⌘K
        </kbd>
      </button>

      {open &&
        typeof document !== 'undefined' &&
        createPortal(
          <div className="fixed inset-0 z-[95] flex items-start justify-center p-4 pt-[12vh]">
            <div
              className="absolute inset-0"
              style={{ background: 'var(--overlay)' }}
              onClick={() => setOpen(false)}
            />
            <div className="animate-fade-in relative z-10 w-full max-w-lg overflow-hidden rounded-2xl border border-border bg-surface shadow-2xl">
              <div className="flex items-center gap-3 border-b border-border px-4">
                <Search className="size-4.5 text-muted-2" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value)
                    setActive(0)
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'ArrowDown') {
                      e.preventDefault()
                      setActive((a) => Math.min(a + 1, results.length - 1))
                    } else if (e.key === 'ArrowUp') {
                      e.preventDefault()
                      setActive((a) => Math.max(a - 1, 0))
                    } else if (e.key === 'Enter' && results[active]) {
                      go(results[active].href)
                    } else if (e.key === 'Escape') {
                      setOpen(false)
                    }
                  }}
                  placeholder="Jump to a page…"
                  className="h-12 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-2"
                />
              </div>
              <ul className="max-h-80 overflow-y-auto p-2">
                {results.length === 0 ? (
                  <li className="px-3 py-8 text-center text-sm text-muted">No results found.</li>
                ) : (
                  results.map((item, i) => (
                    <li key={item.href}>
                      <button
                        onMouseEnter={() => setActive(i)}
                        onClick={() => go(item.href)}
                        className={cn(
                          'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors',
                          i === active ? 'bg-accent-soft text-accent' : 'text-foreground',
                        )}
                      >
                        <item.icon className="size-4.5" />
                        <span className="flex-1">{item.label}</span>
                        {i === active && <CornerDownLeft className="size-3.5 text-muted-2" />}
                      </button>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>,
          document.body,
        )}
    </>
  )
}
