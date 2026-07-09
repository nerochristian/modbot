'use client'

import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

type Ctx = { open: boolean; setOpen: (v: boolean) => void }
const DropdownContext = createContext<Ctx | null>(null)

export function Dropdown({ children, className }: { children: React.ReactNode; className?: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <DropdownContext.Provider value={{ open, setOpen }}>
      <div ref={ref} className={cn('relative', className)}>
        {children}
      </div>
    </DropdownContext.Provider>
  )
}

export function DropdownTrigger({ children }: { children: React.ReactNode }) {
  const ctx = useContext(DropdownContext)!
  return (
    <button
      type="button"
      onClick={() => ctx.setOpen(!ctx.open)}
      aria-haspopup="menu"
      aria-expanded={ctx.open}
      className="focus-ring inline-flex"
    >
      {children}
    </button>
  )
}

export function DropdownMenu({
  children,
  align = 'end',
  className,
}: {
  children: React.ReactNode
  align?: 'start' | 'end'
  className?: string
}) {
  const ctx = useContext(DropdownContext)!
  if (!ctx.open) return null
  return (
    <div
      role="menu"
      className={cn(
        'animate-fade-in absolute z-50 mt-2 min-w-52 overflow-hidden rounded-xl border border-border bg-surface p-1.5 shadow-xl shadow-black/10',
        align === 'end' ? 'right-0' : 'left-0',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function DropdownItem({
  children,
  onClick,
  destructive,
  icon: Icon,
  disabled,
}: {
  children: React.ReactNode
  onClick?: () => void
  destructive?: boolean
  icon?: React.ComponentType<{ className?: string }>
  disabled?: boolean
}) {
  const ctx = useContext(DropdownContext)!
  return (
    <button
      role="menuitem"
      disabled={disabled}
      onClick={() => {
        onClick?.()
        ctx.setOpen(false)
      }}
      className={cn(
        'focus-ring flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors disabled:opacity-50',
        destructive
          ? 'text-danger hover:bg-danger-soft'
          : 'text-foreground hover:bg-surface-2',
      )}
    >
      {Icon && <Icon className="size-4 shrink-0" />}
      {children}
    </button>
  )
}

export function DropdownLabel({ children }: { children: React.ReactNode }) {
  return <div className="px-2.5 py-1.5 text-xs font-medium text-muted-2">{children}</div>
}

export function DropdownSeparator() {
  return <div className="my-1 h-px bg-border" />
}
