'use client'

import { useEffect, useState } from 'react'
import { SettingsCard } from '@/components/dashboard/setting-section'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'

type Widget = { key: string; name: string; description: string; category: string; enabled: boolean }

export default function WidgetsAdminPage() {
  const toast = useToast()
  const [widgets, setWidgets] = useState<Widget[] | null>(null)

  useEffect(() => {
    fetch('/api/admin/widgets').then((r) => r.json()).then((d) => setWidgets(d.widgets)).catch(() => setWidgets([]))
  }, [])

  async function toggle(key: string, enabled: boolean) {
    setWidgets((prev) => prev?.map((w) => (w.key === key ? { ...w, enabled } : w)) ?? null)
    try {
      const res = await fetch('/api/admin/widgets', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, enabled }),
      })
      if (!res.ok) throw new Error()
      toast.success(`Widget ${enabled ? 'enabled' : 'disabled'}`)
    } catch {
      toast.error('Could not update widget')
      fetch('/api/admin/widgets').then((r) => r.json()).then((d) => setWidgets(d.widgets))
    }
  }

  return (
    <SettingsCard
      title="Widget catalog"
      description="Control which widgets are available to users across the workspace. Disabling a widget hides it for everyone."
    >
      {!widgets ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <div className="divide-y divide-border">
          {widgets.map((w) => (
            <div key={w.key} className="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-foreground">{w.name}</p>
                  <Badge tone="neutral">{w.category}</Badge>
                </div>
                <p className="mt-0.5 text-sm text-muted">{w.description}</p>
              </div>
              <Switch checked={w.enabled} onChange={(v) => toggle(w.key, v)} label={`Toggle ${w.name}`} />
            </div>
          ))}
        </div>
      )}
    </SettingsCard>
  )
}
