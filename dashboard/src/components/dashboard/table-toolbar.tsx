'use client'

import { useEffect, useState } from 'react'
import { Search, ArrowDown, ArrowUp, ChevronsUpDown, Columns3, Check } from 'lucide-react'
import { TH } from '@/components/ui/table'
import { Dropdown, DropdownTrigger, DropdownMenu, DropdownLabel } from '@/components/ui/dropdown'
import { cn } from '@/lib/utils'

/** Debounced search box that reports value changes upward. */
export function SearchBox({
  value,
  onChange,
  placeholder = 'Search…',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  const [local, setLocal] = useState(value)
  useEffect(() => setLocal(value), [value])
  useEffect(() => {
    const id = setTimeout(() => {
      if (local !== value) onChange(local)
    }, 300)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [local])

  return (
    <div className="relative w-full sm:w-64">
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-2" />
      <input
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        placeholder={placeholder}
        className="focus-ring h-9 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-foreground placeholder:text-muted-2"
      />
    </div>
  )
}

/** Table header cell that toggles server-side sort and shows direction. */
export function SortableTH({
  column,
  label,
  sort,
  order,
  onToggle,
  className,
}: {
  column: string
  label: string
  sort: string
  order: 'asc' | 'desc'
  onToggle: (column: string) => void
  className?: string
}) {
  const active = sort === column
  return (
    <TH className={className}>
      <button
        onClick={() => onToggle(column)}
        className="focus-ring -mx-1 inline-flex items-center gap-1 rounded px-1 py-0.5 hover:text-foreground"
      >
        {label}
        {active ? (
          order === 'desc' ? (
            <ArrowDown className="size-3.5" />
          ) : (
            <ArrowUp className="size-3.5" />
          )
        ) : (
          <ChevronsUpDown className="size-3.5 opacity-50" />
        )}
      </button>
    </TH>
  )
}

/** Column visibility toggler backed by the saved dashboard config. */
export function ColumnsMenu({
  columns,
  visible,
  onChange,
}: {
  columns: { key: string; label: string }[]
  visible: string[]
  onChange: (visible: string[]) => void
}) {
  function toggle(key: string) {
    if (visible.includes(key)) {
      if (visible.length <= 1) return // keep at least one column
      onChange(visible.filter((c) => c !== key))
    } else {
      onChange([...columns.map((c) => c.key).filter((k) => visible.includes(k) || k === key)])
    }
  }

  return (
    <Dropdown>
      <DropdownTrigger>
        <span className="focus-ring inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-surface px-3 text-sm font-medium text-foreground hover:bg-surface-2">
          <Columns3 className="size-4" />
          <span className="hidden sm:inline">Columns</span>
        </span>
      </DropdownTrigger>
      <DropdownMenu>
        <DropdownLabel>Toggle columns</DropdownLabel>
        {columns.map((c) => {
          const on = visible.includes(c.key)
          return (
            <button
              key={c.key}
              onClick={() => toggle(c.key)}
              className="focus-ring flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm text-foreground hover:bg-surface-2"
            >
              <span
                className={cn(
                  'flex size-4 items-center justify-center rounded border',
                  on ? 'border-accent bg-accent text-accent-foreground' : 'border-border-strong',
                )}
              >
                {on && <Check className="size-3" />}
              </span>
              {c.label}
            </button>
          )
        })}
      </DropdownMenu>
    </Dropdown>
  )
}
