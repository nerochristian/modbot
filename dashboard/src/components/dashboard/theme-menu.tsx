'use client'

import { Sun, Moon, Monitor, Check } from 'lucide-react'
import { Dropdown, DropdownTrigger, DropdownMenu, DropdownLabel } from '@/components/ui/dropdown'
import { useConfigStore } from '@/lib/store'
import { ACCENT_COLORS, type ThemeMode } from '@/lib/dashboard-config'
import { cn } from '@/lib/utils'

const OPTIONS: { value: ThemeMode; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
]

export function ThemeMenu() {
  const theme = useConfigStore((s) => s.config.theme)
  const accent = useConfigStore((s) => s.config.accent)
  const setTheme = useConfigStore((s) => s.setTheme)
  const setAccent = useConfigStore((s) => s.setAccent)

  const Icon = theme === 'dark' ? Moon : theme === 'light' ? Sun : Monitor

  return (
    <Dropdown>
      <DropdownTrigger>
        <span className="focus-ring inline-flex size-9 items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface-2 hover:text-foreground">
          <Icon className="size-4.5" />
        </span>
      </DropdownTrigger>
      <DropdownMenu className="min-w-56">
        <DropdownLabel>Theme</DropdownLabel>
        <div className="grid grid-cols-3 gap-1 p-1">
          {OPTIONS.map((o) => (
            <button
              key={o.value}
              onClick={() => setTheme(o.value)}
              className={cn(
                'focus-ring flex flex-col items-center gap-1.5 rounded-lg border px-2 py-2.5 text-xs font-medium transition-colors',
                theme === o.value
                  ? 'border-accent bg-accent-soft text-accent'
                  : 'border-border text-muted hover:bg-surface-2',
              )}
            >
              <o.icon className="size-4" />
              {o.label}
            </button>
          ))}
        </div>
        <DropdownLabel>Accent</DropdownLabel>
        <div className="flex flex-wrap gap-1.5 p-2">
          {ACCENT_COLORS.map((c) => (
            <button
              key={c.key}
              onClick={() => setAccent(c.key)}
              aria-label={c.label}
              className="focus-ring flex size-6 items-center justify-center rounded-full ring-2 ring-transparent transition-all hover:scale-110"
              style={{ backgroundColor: c.value, boxShadow: accent === c.key ? `0 0 0 2px var(--surface), 0 0 0 4px ${c.value}` : undefined }}
            >
              {accent === c.key && <Check className="size-3.5 text-white" />}
            </button>
          ))}
        </div>
      </DropdownMenu>
    </Dropdown>
  )
}
