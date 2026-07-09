'use client'

import { Check, Sun, Moon, Monitor } from 'lucide-react'
import { SettingsCard, SettingRow } from '@/components/dashboard/setting-section'
import { SegmentedControl } from '@/components/ui/segmented'
import { useConfigStore } from '@/lib/store'
import { ACCENT_COLORS, type Density, type ThemeMode } from '@/lib/dashboard-config'
import { cn } from '@/lib/utils'

export default function AppearanceSettingsPage() {
  const theme = useConfigStore((s) => s.config.theme)
  const accent = useConfigStore((s) => s.config.accent)
  const density = useConfigStore((s) => s.config.density)
  const setTheme = useConfigStore((s) => s.setTheme)
  const setAccent = useConfigStore((s) => s.setAccent)
  const setDensity = useConfigStore((s) => s.setDensity)

  return (
    <SettingsCard title="Appearance" description="Personalize how Nebula looks. Changes save automatically.">
      <div className="divide-y divide-border">
        <SettingRow label="Theme" description="Choose light, dark, or match your system.">
          <SegmentedControl
            aria-label="Theme"
            value={theme}
            onChange={(v) => setTheme(v as ThemeMode)}
            options={[
              { label: <Sun className="size-4" />, value: 'light' },
              { label: <Moon className="size-4" />, value: 'dark' },
              { label: <Monitor className="size-4" />, value: 'system' },
            ]}
          />
        </SettingRow>

        <SettingRow label="Accent color" description="Used for highlights, buttons, and charts.">
          <div className="flex flex-wrap gap-2">
            {ACCENT_COLORS.map((c) => (
              <button
                key={c.key}
                onClick={() => setAccent(c.key)}
                aria-label={c.label}
                className="flex size-8 items-center justify-center rounded-full transition-transform hover:scale-110"
                style={{ backgroundColor: c.value, boxShadow: accent === c.key ? `0 0 0 2px var(--card), 0 0 0 4px ${c.value}` : undefined }}
              >
                {accent === c.key && <Check className="size-4 text-white" />}
              </button>
            ))}
          </div>
        </SettingRow>

        <SettingRow label="Density" description="Compact reduces spacing to fit more on screen.">
          <SegmentedControl
            aria-label="Density"
            value={density}
            onChange={(v) => setDensity(v as Density)}
            options={[
              { label: 'Comfortable', value: 'comfortable' },
              { label: 'Compact', value: 'compact' },
            ]}
          />
        </SettingRow>
      </div>

      <div className={cn('mt-6 rounded-xl border border-border p-4')}>
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-2">Preview</p>
        <div className="flex flex-wrap items-center gap-3">
          <button className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground">Primary</button>
          <button className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground">Secondary</button>
          <span className="rounded-full bg-accent-soft px-3 py-1 text-xs font-medium text-accent">Accent badge</span>
        </div>
      </div>
    </SettingsCard>
  )
}
